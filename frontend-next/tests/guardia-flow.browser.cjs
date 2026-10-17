const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const modules=[],ids=new Map();
const mocks={
 '@clerk/nextjs':`const getToken=async()=>'synthetic';exports.useAuth=()=>({getToken});`,
 '@/components/IdentificacionVisita':`exports.default=()=>null;`,
 '@/lib/api':`exports.api={get:async p=>{window.calls.push(p);
 if(p==='/condominios/')return [{condominio_id:'a',nombre:'Caseta A'},{condominio_id:'b',nombre:'Caseta B'}];
 if(p.includes('reglas-acceso'))return {exigir_autorizacion:true,exigir_proposito:true,tipos_visita:['eventual']};
 if(p.includes('/condominio/'))return window.rows;
 if(p.startsWith('/qr/validar/')){window.qrWrites++;const v=window.rows.find(x=>p.includes('/'+x.visita_id+'/'));v.estado='entrada_registrada';v.entrada_registrada_en=new Date().toISOString();return {status:'aprobado'};}
 if(window.readFails)throw Error('Failed to fetch');
 const id=p.split('/')[2].split('?')[0];const v=window.rows.find(x=>x.visita_id===id);if(!v)throw Error('Visita no encontrada');return {...v};
 },patch:async p=>{window.writes++;const id=p.split('/')[2];const v=window.rows.find(x=>x.visita_id===id);v.estado='salida_registrada';v.salida_registrada_en=new Date().toISOString();if(window.uncertain)window.readFails=true;throw Error('Failed to fetch');}};`,
};
function bundle(name, parent=path.join(process.cwd(),'entry.js')) {
  const alias = name.startsWith('@/') ? path.join(process.cwd(), 'src', name.slice(2)) : null;
  const candidate = alias || (name.startsWith('.') ? path.resolve(path.dirname(parent), name) : null);
  const local = candidate && ['', '.tsx', '.ts', '.js'].map(ext => candidate + ext).find(file => fs.existsSync(file) && fs.statSync(file).isFile());
  const file = mocks[name] ? name : local || require.resolve(name, {paths:[path.dirname(parent)]});
  if(ids.has(file)) return ids.get(file);
  const id=modules.length; ids.set(file,id); modules.push('');
  let source=mocks[name] || fs.readFileSync(file,'utf8');
  if(/\.tsx?$/.test(file)) source=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText;
  source=source.replace(/process\.env\.NODE_ENV/g,'"production"').replace(/require\(["']([^"']+)["']\)/g,(_,dep)=>`require(${bundle(dep,file)})`);
  modules[id]=`function(require,module,exports){${source}\n}`;
  return id;
}

(async()=>{
 const react=bundle('react'),dom=bundle('react-dom/client'),component=bundle(path.join(process.cwd(),'src/app/dashboard/guardia/GuardiaClient.tsx'));
 const script=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}require(${dom}).createRoot(document.getElementById('root')).render(require(${react}).createElement(require(${component}).default));`;
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  await page.route('**/*',r=>r.fulfill({contentType:'text/html',body:'<div id="root"></div>'}));
  async function open(uncertain=false){
   await page.goto('http://127.0.0.1:47893/');
   await page.evaluate(uncertain=>{
    window.calls=[];window.writes=0;window.qrWrites=0;window.readFails=false;window.uncertain=uncertain;
    const now=Date.now();const base={condominio_id:'a',nombre_visitante:'María Pérez',tipo_visita:'eventual',proposito:'Entrega',autorizada_por:'resident',autorizada_en:new Date(now-3600000).toISOString(),vigencia:new Date(now-86400000).toISOString(),qr_vigencia:new Date(now-80000000).toISOString(),estado:'entrada_registrada',entrada_registrada_en:new Date(now-86400000).toISOString(),salida_registrada_en:null,qr_token:'expired'};
    window.rows=[{...base,visita_id:'one',casa_unidad:'24',placa:'ABC123'},{...base,visita_id:'two',casa_unidad:'25'}, {...base,visita_id:'closed',casa_unidad:'26',estado:'salida_registrada',salida_registrada_en:new Date(now-3600000).toISOString()}, {...base,visita_id:'qr',nombre_visitante:'Pedro QR',casa_unidad:'30',estado:'pendiente',entrada_registrada_en:null,vigencia:new Date(now).toISOString(),qr_vigencia:new Date(now+3600000).toISOString(),qr_token:'valid'}];
   },uncertain);
   await page.addScriptTag({content:script});
   await page.getByRole('button',{name:'Registrar salida',exact:true}).waitFor();
  }
  await open();
  assert.equal(await page.getByText('María Pérez',{exact:true}).count(),0);
  await page.getByRole('button',{name:'Registrar salida',exact:true}).click();
  await page.getByRole('button',{name:'No tiene QR',exact:true}).click();
  await page.getByLabel('Nombre, vivienda, placa o referencia de visita').fill('maria');
  await page.getByRole('button',{name:'Buscar visita',exact:true}).click();
  await page.getByText('2 coincidencias. Elige la persona y el destino correctos.').waitFor();
  assert.equal(await page.evaluate(()=>window.writes),0);
  await page.getByRole('button',{name:/María Pérez · 24/}).click();
  await page.getByRole('button',{name:'Registrar salida de María Pérez',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Registrar salida de María Pérez',exact:true}).isDisabled(),true);
  await page.getByLabel('Confirmé que la persona y el destino corresponden a esta visita.').check();
  await page.getByRole('button',{name:'Registrar salida de María Pérez',exact:true}).click();
  await page.getByRole('heading',{name:'Salida registrada',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.writes),1);
  // A lost response plus unavailable read locks retry until read-back succeeds.
  await open(true);
  await page.getByRole('button',{name:'Registrar salida',exact:true}).click();
  await page.getByRole('button',{name:'No tiene QR',exact:true}).click();
  await page.getByLabel('Nombre, vivienda, placa o referencia de visita').fill('ABC123');
  await page.getByRole('button',{name:'Buscar visita',exact:true}).click();
  await page.getByRole('button',{name:/María Pérez · 24/}).click();
  await page.getByLabel('Confirmé que la persona y el destino corresponden a esta visita.').check();
  await page.getByRole('button',{name:'Registrar salida de María Pérez',exact:true}).click();
  await page.getByRole('button',{name:'Comprobar registro',exact:true}).waitFor();
  assert.equal(await page.getByLabel('Estás operando en').isDisabled(),true);
  assert.equal(await page.getByRole('button',{name:'Registrar salida de María Pérez',exact:true}).count(),0);
  await page.evaluate(()=>{window.readFails=false;});
  await page.getByRole('button',{name:'Comprobar registro',exact:true}).click();
  await page.getByRole('heading',{name:'Salida registrada',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.writes),1);
  // Scanning only identifies: mutation happens after explicit identity confirmation.
  await open();
  await page.getByRole('button',{name:'Registrar entrada',exact:true}).click();
  await page.getByText('Usar lector QR o pegar código',{exact:true}).click();
  await page.getByLabel('Código AXS').fill('AXS|qr|valid');
  await page.getByRole('button',{name:'Revisar QR',exact:true}).click();
  await page.getByRole('heading',{name:'Pedro QR',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.qrWrites),0);
  await page.getByLabel('Confirmé que la persona y el destino corresponden a esta visita.').check();
  await page.getByRole('button',{name:'Registrar entrada de Pedro QR',exact:true}).click();
  await page.getByRole('heading',{name:'Entrada registrada',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.qrWrites),1);
  console.log('PASS: guided recovery, homonyms, plate, expired open visit, confirmed QR, uncertain response reconciliation without duplicate writes.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
