// Real React form with synthetic transport; all external network is blocked.
const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const modules=[],ids=new Map();
const mocks={
'@clerk/nextjs':`const getToken=async()=>'synthetic';exports.useAuth=()=>({userId:'operator',getToken});`,
'next/navigation':`exports.useRouter=()=>({push:()=>{},back:()=>{}});`,
'@/lib/api':`exports.api={get:async p=>{
 if(p==='/auth/me'){if(window.profileError)throw Error('Profile unavailable');return {rol:window.role,condominio_id:'a1'}}
 if(p==='/condominios/')return [{condominio_id:'a1',nombre:'Alpha'},{condominio_id:'b1',nombre:'Beta'}];
 if(p==='/preregistro/reloj')return {utc:new Date().toISOString()};
 if(p.endsWith('/reglas-acceso')){if(window.rulesError)throw Error('Rules unavailable');return {exigir_proposito:false,exigir_autorizacion:true,tipos_visita:[]}}
 if(p.endsWith('/destinos')){if(window.delayA&&p.includes('/a1/'))await new Promise(r=>window.releaseA=r);return [{destino_id:p.includes('/a1/')?'home-a':'home-b',nombre:'Synthetic home'}]}
 throw Error('Unexpected GET '+p);
 },post:async(p,b)=>{window.calls.push({p,b});return {visita_id:'synthetic',qr_base64:'',qr_vigencia:new Date().toISOString(),qr_inicio:null}}};`
};
function bundle(name,parent=path.join(process.cwd(),'entry.js')){
 const f=mocks[name]?name:name.startsWith('@/')?require.resolve(path.join(process.cwd(),'src',name.slice(2))+ (fs.existsSync(path.join(process.cwd(),'src',name.slice(2))+'.tsx')?'.tsx':'.ts')):require.resolve(name,{paths:[path.dirname(parent)]});
 if(ids.has(f))return ids.get(f);const id=modules.length;ids.set(f,id);modules.push('');
 let s=mocks[name]||fs.readFileSync(f,'utf8');if(/\.tsx?$/.test(f))s=ts.transpileModule(s,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText;
 s=s.replace(/process\.env\.NODE_ENV/g,'"production"').replace(/require\(["']([^"']+)["']\)/g,(_,d)=>`require(${bundle(d,f)})`);
 modules[id]=`function(require,module,exports){${s}\n}`;return id;
}
(async()=>{
 const r=bundle('react'),d=bundle('react-dom/client'),c=bundle(path.join(process.cwd(),'src/app/dashboard/residente/nueva/PreregistroClient.tsx'));
 const js=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}require(${d}).createRoot(document.getElementById('root')).render(require(${r}).createElement(require(${c}).default));`;
 const browser=await chromium.launch({headless:true});
 try {
 async function pageFor(role,flags={}) {
  const page=await browser.newPage();
  await page.route('**/*',route=>route.request().url()==='http://127.0.0.1:47891/'?route.fulfill({contentType:'text/html',body:'<div id="root"></div>'}):route.abort());
  await page.goto('http://127.0.0.1:47891/');
  await page.evaluate(({role,flags})=>Object.assign(window,{role,calls:[]},flags),{role,flags});
  await page.addScriptTag({content:js});return page;
 }
 for(const role of ['MSP_ADMIN','ADMIN_CONDOMINIO']) {
  const page=await pageFor(role);
  await page.getByLabel('Condominio',{exact:true}).waitFor();
  const submit=page.getByRole('button',{name:'Generar QR de Acceso'});
  assert.equal(await submit.isDisabled(),true);
  await page.getByLabel('Condominio',{exact:true}).selectOption('a1');
  await page.getByLabel('Destino',{exact:true}).selectOption('home-a');
  await page.getByPlaceholder('Ej. Juan Pérez').fill('Synthetic');
  await submit.click();await page.getByRole('heading',{name:'QR Generado'}).waitFor();
  const calls=await page.evaluate(()=>window.calls);
  assert.equal(calls.length,1);assert.equal(calls[0].b.condominio_id,'a1');assert.equal(calls[0].b.destino_id,'home-a');await page.close();
 }
 const resident=await pageFor('RESIDENTE');
 await resident.getByPlaceholder('Ej. Juan Pérez').fill('Resident');
 await resident.getByRole('button',{name:'Generar QR de Acceso'}).click();
 await resident.getByRole('heading',{name:'QR Generado'}).waitFor();
 const payload=await resident.evaluate(()=>window.calls[0].b);
 assert.equal('condominio_id' in payload,false);assert.equal('destino_id' in payload,false);await resident.close();
 const race=await pageFor('MSP_ADMIN',{delayA:true});
 await race.getByLabel('Condominio',{exact:true}).selectOption('a1');
 await race.waitForFunction(()=>!!window.releaseA);
 await race.getByLabel('Condominio',{exact:true}).selectOption('b1');
 await race.getByLabel('Destino',{exact:true}).selectOption('home-b');
 await race.evaluate(()=>window.releaseA());
 await race.getByPlaceholder('Ej. Juan Pérez').fill('Race');
 await race.getByRole('button',{name:'Generar QR de Acceso'}).click();
 await race.getByRole('heading',{name:'QR Generado'}).waitFor();
 assert.equal(await race.evaluate(()=>window.calls[0].b.destino_id),'home-b');await race.close();
 for(const [role,flags] of [['GUARDIA',{}],['MSP_ADMIN',{profileError:true}],['RESIDENTE',{rulesError:true}]]) {
  const page=await pageFor(role,flags);await page.getByRole('alert').waitFor();
  assert.equal(await page.getByRole('button',{name:'Generar QR de Acceso'}).isDisabled(),true);
  assert.equal(await page.evaluate(()=>window.calls.length),0);await page.close();
 }
 console.log('PASS: admin destination, resident payload, stale catalog race and fail-closed profile/role/rules. Synthetic only.');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
