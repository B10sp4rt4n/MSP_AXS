// Optional: npm install --no-save playwright; npx playwright install chromium
// All network requests except the synthetic page are blocked.
const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const modules=[],ids=new Map();
const mocks={
'@clerk/nextjs':`exports.useAuth=()=>({userId:'operator',getToken:async()=>'synthetic'});`,
'@/lib/api':`exports.api={get:async p=>{if(window.denied||window.offline)throw Error('Requiere autoridad o conexión');return structuredClone(p.endsWith('/contratos')?window.contracts:window.inventory)},post:async(p,b)=>{window.calls.push({p,b});if(p.endsWith('/contratos')){let c=window.contracts.find(c=>c.contract_id===b.contract_id);if(!c){c={...b,version:window.contracts.length+1,opened_at:'2030-01-15T18:00:00',closed_at:null};window.contracts.push(c);window.inventory.msp_id=b.msp_id;}if(window.failOnce){window.failOnce=false;throw Error('network after commit')}return c;}if(p.endsWith('/baja')){window.contracts.find(c=>c.contract_id===b.contract_id).closed_at='2030-01-15T19:00:00';window.inventory.msp_id=null;return {event_uid:'closed',contract_id:b.contract_id}}return {scope_id:12}},put:async()=>({})};`};
function bundle(name,parent=path.join(process.cwd(),'entry.js')){
 const f=mocks[name]?name:name.startsWith('@/')?path.join(process.cwd(),'src',name.slice(2))+'.ts':require.resolve(name,{paths:[path.dirname(parent)]});
 if(ids.has(f))return ids.get(f);const id=modules.length;ids.set(f,id);modules.push('');
 let s=mocks[name]||fs.readFileSync(f,'utf8');if(/\.tsx?$/.test(f))s=ts.transpileModule(s,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText;
 s=s.replace(/process\.env\.NODE_ENV/g,'"production"').replace(/require\(["']([^"']+)["']\)/g,(_,d)=>`require(${bundle(d,f)})`);
 modules[id]=`function(require,module,exports){${s}\n}`;return id;
}
(async()=>{
 const r=bundle('react'),d=bundle('react-dom/client'),c=bundle(path.join(process.cwd(),'src/components/ProviderConsole.tsx'));
 const js=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}require(${d}).createRoot(document.getElementById('root')).render(require(${r}).createElement(require(${c}).default));`;
 const browser=await chromium.launch({headless:true});try{
 const page=await browser.newPage();await page.route('**/*',route=>route.request().url()==='http://127.0.0.1:47891/'?route.fulfill({contentType:'text/html',body:'<div id="root"></div>'}):route.abort());
 await page.goto('http://127.0.0.1:47891/');await page.evaluate(()=>{window.calls=[];window.contracts=[];window.inventory={condominio_id:'synthetic',msp_id:null,scopes:[]};window.denied=true});await page.addScriptTag({content:js});
 const click=name=>page.getByRole('button',{name,exact:true}).click();
 await page.getByLabel('ID del condominio').fill('synthetic');await click('Consultar');await page.getByRole('alert').waitFor();assert.equal(await page.getByRole('button',{name:'Revisar apertura'}).count(),0);
 await page.evaluate(()=>{window.denied=false;window.failOnce=true});await click('Consultar');
 for(let i=1;i<=2;i++){
 await page.getByLabel('ID del proveedor existente').fill('same-msp');await page.getByLabel('Referencia del contrato o evidencia').fill('synthetic-'+i);await click('Revisar apertura');await click('Confirmar operación');
 if(i===1){await page.getByRole('alert').waitFor();await click('Confirmar operación')}
 await page.getByLabel('Motivo de baja').fill('fin');await click('Revisar baja');await click('Confirmar operación');await page.getByLabel('ID del proveedor existente').waitFor();
 }
 const data=await page.evaluate(()=>({calls:window.calls,contracts:window.contracts}));const opens=data.calls.filter(c=>c.p.endsWith('/contratos'));
 assert.equal(opens[0].b.contract_id,opens[1].b.contract_id);assert.notEqual(opens[1].b.contract_id,opens[2].b.contract_id);assert.equal(data.contracts.length,2);assert.ok(data.contracts.every(c=>c.closed_at));
 assert.deepEqual(data.calls.filter(c=>c.p.endsWith('/baja')).map(c=>c.b.contract_id),data.contracts.map(c=>c.contract_id));
 // Change evidence to prepare a third contract; simulate refresh failure after success.
 await page.getByLabel('Referencia del contrato o evidencia').fill('third');await click('Revisar apertura');await page.evaluate(()=>{window.offline=true});await click('Confirmar operación');await page.getByRole('alert').waitFor();assert.equal(await page.getByRole('button',{name:'Revisar baja'}).count(),0);
 console.log('PASS: browser authorization denial, two contract cycles, stable UUID retry, scoped exits, failed refresh hides controls. Synthetic transport only.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
