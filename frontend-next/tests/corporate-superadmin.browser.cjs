// Browser rehearsal: all API/Clerk transport is synthetic and all external traffic blocked.
// This test never touches Railway, Vercel, Neon, or a real Clerk account.
const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const modules=[],ids=new Map();
const mocks={
 '@clerk/nextjs': `const getToken=async()=> 'synthetic-test-token';
exports.useAuth=()=>({getToken,isLoaded:true,userId:'global-fixture'});`,
 '@/lib/api': `class ApiError extends Error{constructor(message,status){super(message);this.status=status}}
exports.ApiError=ApiError;
exports.api={
  get:async p=>{
    window.__reads.push(p);
    if(window.__deny)throw new ApiError('No autorizado',403);
    if(window.__disabled)throw new ApiError('Off',404);
    if(p==='/plataforma/corporativo/acceso')return {authorized:true};
    throw Error('Unexpected GET '+p);
  },
  post:async(p,b)=>{
    window.__calls.push({method:'POST',p,b});
    if(p==='/plataforma/corporativo/empresas'){
      if(!window.__companies[b.request_id])window.__companies[b.request_id]={
        tenant_id:'corp_'+b.request_id.replaceAll('-',''),nombre:b.nombre,msp_id:b.msp_id,
        owner_user_id:b.owner_user_id,modalidad:'corporativo',directorio_habilitado:false,
        privacy_contact:b.privacy_contact,privacy_notice_version:b.privacy_notice_version};
      const row=window.__companies[b.request_id];
      if(row.nombre!==b.nombre)throw new ApiError('Referencia utilizada',409);
      if(window.__failOnce){window.__failOnce=false;throw new Error('ACK incierto tras commit')}
      return structuredClone(row);
    }
    if(p.endsWith('/habilitar-directorio')){
      if(!window.__capabilities)throw new ApiError('Cuotas ausentes',409);
      if(b.confirmacion!==true)throw new ApiError('Confirmación obligatoria',422);
      const id=p.split('/')[4];
      const row=Object.values(window.__companies).find(v=>v.tenant_id===id);
      if(!row)throw new ApiError('Empresa no existe',404);
      row.directorio_habilitado=true;return structuredClone(row);
    }
    throw Error('Unexpected POST '+p);
  },
  put:async(p,b)=>{
    window.__calls.push({method:'PUT',p,b});
    if(!p.endsWith('/capacidades'))throw Error('Unexpected PUT '+p);
    window.__capabilities=b;return {tenant_id:p.split('/')[4],...b};
  }
};`
};
function bundle(name,parent=path.join(process.cwd(),'entry.js')){
 const f=mocks[name]?name:name.startsWith('@/')?
  require.resolve(path.join(process.cwd(),'src',name.slice(2))+(fs.existsSync(path.join(process.cwd(),'src',name.slice(2))+'.tsx')?'.tsx':'.ts')):
  require.resolve(name,{paths:[path.dirname(parent)]});
 if(ids.has(f))return ids.get(f);
 const id=modules.length;ids.set(f,id);modules.push('');
 let s=mocks[name]||fs.readFileSync(f,'utf8');
 if(/\.tsx?$/.test(f))s=ts.transpileModule(s,{compilerOptions:{
    module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
 s=s.replace(/process\.env\.NODE_ENV/g,'"production"')
    .replace(/require\(["']([^"']+)["']\)/g,(_,d)=>`require(${bundle(d,f)})`);
 modules[id]=`function(require,module,exports){${s}\n}`;return id;
}
(async()=>{
 const react=bundle('react'),dom=bundle('react-dom/client');
 const comp=bundle(path.join(process.cwd(),'src/app/dashboard/corporativo-superadmin/CorporativoSuperadminClient.tsx'));
 const js=`const mods=[${modules.join(',')}],cache={};
 function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}
 require(${dom}).createRoot(document.getElementById('root')).render(
 require(${react}).createElement(require(${comp}).default));`;
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:360,height:800}});
  await page.route('**/*',route=>route.request().url()==='http://127.0.0.1:47891/'?
    route.fulfill({contentType:'text/html',body:'<div id="root"></div>'}):route.abort());
  await page.goto('http://127.0.0.1:47891/');
  await page.evaluate(()=>{window.__reads=[];window.__calls=[];window.__companies={};
    window.__capabilities=null;window.__deny=true;window.__disabled=false;window.__failOnce=false;});
  await page.addScriptTag({content:js});
  const click=name=>page.getByRole('button',{name,exact:true}).click();
  await page.getByRole('alert').getByText('Tu cuenta no tiene autoridad GLOBAL.').waitFor();
  assert.equal(await page.getByRole('button',{name:'Crear empresa deshabilitada'}).count(),0);
  assert.equal(await page.evaluate(()=>window.__calls.length),0);
  await page.evaluate(()=>window.__deny=false);
  await click('Reintentar comprobación');
  await page.getByRole('button',{name:'Crear empresa deshabilitada'}).waitFor();
  await page.getByLabel('Nombre de empresa').fill('Empresa Sintética');
  await page.getByLabel('ID del MSP responsable').fill('msp_synthetic');
  await page.getByLabel('ID del propietario inicial').fill('owner_synthetic');
  await page.getByLabel('Correo del responsable de privacidad').fill('privacidad@example.test');
  await page.getByLabel('URL HTTPS del aviso de privacidad').fill('https://example.test/aviso');
  await page.getByLabel('Versión del aviso').fill('2026-10');
  await page.evaluate(()=>window.__failOnce=true);
  await click('Crear empresa deshabilitada');
  await page.getByRole('alert').getByText('ACK incierto tras commit').waitFor();
  const one=await page.evaluate(()=>window.__calls[0].b.request_id);
  assert.match(one,/^[0-9a-f-]{36}$/);
  assert.equal(await page.evaluate(()=>Object.keys(window.__companies).length),1);
  await click('Crear empresa deshabilitada');
  await page.getByText('Capacidades de directorio').waitFor();
  assert.equal(await page.evaluate(()=>window.__calls[1].b.request_id),one,'Retry must preserve UUID');
  assert.equal(await page.evaluate(()=>Object.keys(window.__companies).length),1);
  await page.getByLabel('Máximo de sedes').fill('2');
  await page.getByLabel('Destinos máximos por sede').fill('10');
  await click('Guardar capacidades');
  await page.getByText('Habilitación del directorio',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Habilitar directorio'}).isDisabled(),true);
  assert.equal(await page.evaluate(()=>window.__calls.filter(c=>c.p.endsWith('/habilitar-directorio')).length),0);
  await page.getByRole('checkbox').check();
  await click('Habilitar directorio');
  await page.getByRole('button',{name:'Directorio habilitado'}).waitFor();
  assert.equal(await page.evaluate(()=>window.__calls.filter(c=>c.p.endsWith('/habilitar-directorio')).length),1);
  assert.equal(await page.evaluate(()=>Object.values(window.__companies)[0].directorio_habilitado),true);
  for(const width of [320,360,1280]){
    await page.setViewportSize({width,height:800});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,
      'Horizontal overflow at '+width);
  }
  await click('Comenzar otra alta');
  await page.getByRole('button',{name:'Crear empresa deshabilitada'}).waitFor();
  assert.equal(await page.getByLabel('Nombre de empresa').inputValue(),'');
  assert.equal(await page.evaluate(()=>Object.keys(window.__companies).length),1);
  console.log('PASS: synthetic GLOBAL denial, staged flow, idempotent UUID after ambiguous ACK, explicit activation, reset and 320/360/1280px widths. No real network.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
