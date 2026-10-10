// Real report component and bitacora, synthetic transport only.
const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const modules=[],ids=new Map();
const mocks={
'@clerk/nextjs':`const getToken=async()=>'synthetic';exports.useAuth=()=>({getToken});`,
'@/lib/api':`exports.api={get:async p=>{
 window.calls.push(p);if(window.fail)throw Error('Consulta no disponible');
 if(p.startsWith('/bitacora/'))return {items:[],siguiente:null,pendientes_entrega_condominio:0};
 if(window.delay)await new Promise(r=>window.release=r);
 return {condominio_id:'a',condominio:'Condominio sintético',desde:'2030-01-15',hasta:'2030-01-15',generado_en:'2030-01-15T18:00:00Z',pendientes_entrega_condominio:2,total:26,resumen:{entrada:26,salida:0,cancelacion:0,rechazo:0,otro:0},items:Array.from({length:26},(_,i)=>({id:i,fecha:'2030-01-15T18:00:00Z',visita_id:'visit-'+i,actor_id:'guard-a',categoria:'entrada',accion:'registrar',resultado:'exito',estado:'entrada_registrada',destino:'101',motivo:'Entrada registrada'}))};
 },download:async p=>{window.downloads.push(p);return new Blob(['synthetic export'])}};`
};
function bundle(name,parent=path.join(process.cwd(),'entry.js')){
 const f=mocks[name]?name:name.startsWith('@/')?require.resolve(path.join(process.cwd(),'src',name.slice(2))+ (fs.existsSync(path.join(process.cwd(),'src',name.slice(2))+'.tsx')?'.tsx':'.ts')):require.resolve(name,{paths:[path.dirname(parent)]});
 if(ids.has(f))return ids.get(f);const id=modules.length;ids.set(f,id);modules.push('');
 let s=mocks[name]||fs.readFileSync(f,'utf8');if(/\.tsx?$/.test(f))s=ts.transpileModule(s,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText;
 s=s.replace(/process\.env\.NODE_ENV/g,'"production"').replace(/require\(["']([^"']+)["']\)/g,(_,d)=>`require(${bundle(d,f)})`);
 modules[id]=`function(require,module,exports){${s}\n}`;return id;
}
(async()=>{
 const r=bundle('react'),d=bundle('react-dom/client'),c=bundle(path.join(process.cwd(),'src/components/ReportesOperacion.tsx'));
 const js=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}const root=require(${d}).createRoot(document.getElementById('root'));window.renderTenant=t=>root.render(require(${r}).createElement(require(${c}).default,{condominioId:t,key:t}));window.renderTenant('a');`;
 const browser=await chromium.launch({headless:true});
 try {
 const page=await browser.newPage({viewport:{width:390,height:844}});
 await page.route('**/*',route=>route.request().url()==='http://127.0.0.1:47891/'?route.fulfill({contentType:'text/html',body:'<div id="root"></div>'}):route.abort());
 await page.goto('http://127.0.0.1:47891/');
 await page.evaluate(()=>Object.assign(window,{calls:[],downloads:[]}));
 await page.addScriptTag({content:js});
 await page.getByLabel('Desde',{exact:true}).fill('2030-01-15');
 await page.getByLabel('Hasta',{exact:true}).fill('2030-01-15');
 await page.getByRole('button',{name:'Consultar reporte',exact:true}).click();
 await page.getByText('26 eventos recibidos',{exact:true}).waitFor();
 assert.equal(await page.locator('article').count(),25);
 assert.ok((await page.getByRole('status').textContent()).includes('Reporte provisional'));
 await page.getByRole('button',{name:'Siguiente',exact:true}).click();
 assert.equal(await page.locator('article').count(),1);
 await page.getByRole('button',{name:'Ver historial: visit-25',exact:true}).click();
 await page.getByText('Sin eventos recibidos.',{exact:true}).waitFor();
 assert.ok((await page.evaluate(()=>window.calls)).some(p=>p.includes('visita_id=visit-25')));
 const download=page.waitForEvent('download');
 await page.getByRole('button',{name:'Descargar Excel',exact:true}).click();
 assert.ok((await download).suggestedFilename().endsWith('.xlsx'));
 assert.ok((await page.evaluate(()=>window.downloads[0])).includes('desde=2030-01-15&hasta=2030-01-15&formato=xlsx'));
 await page.getByLabel('Destino exacto',{exact:true}).fill('102');
 assert.equal(await page.getByRole('button',{name:'Descargar Excel',exact:true}).isDisabled(),true);
 await page.evaluate(()=>window.fail=true);
 await page.getByRole('button',{name:'Consultar reporte',exact:true}).click();
 await page.getByRole('alert').waitFor();
 assert.equal(await page.locator('article').count(),0);
 await page.evaluate(()=>{window.fail=false;window.delay=true});
 await page.getByRole('button',{name:'Consultar reporte',exact:true}).click();
 await page.waitForFunction(()=>!!window.release);
 await page.evaluate(()=>window.renderTenant('b'));
 await page.getByRole('button',{name:'Consultar reporte',exact:true}).waitFor();
 await page.evaluate(()=>window.release());
 assert.equal(await page.locator('article').count(),0);
 console.log('PASS: pagination, pending warning, visit history, export filters, stale-filter blocking, errors and tenant-switch race. Synthetic transport only.');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
