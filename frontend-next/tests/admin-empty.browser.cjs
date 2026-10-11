const fs = require('fs'), path = require('path'), ts = require('typescript');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const modules = [], ids = new Map();
const mocks = {
  'next/navigation': `exports.useRouter=()=>({push:()=>{}});`,
  '@clerk/nextjs': `const getToken=async()=>'synthetic';exports.useAuth=()=>({getToken});`,
  '@/lib/api': `exports.api={get:async p=>{window.calls.push(p);if(p!='/condominios/')return [];return new Promise((resolve,reject)=>{window.finish=()=>window.mode==='error'?reject(Error('offline')):resolve(window.mode==='empty'?[]:[{condominio_id:'a',nombre:'Condominio A'}]);});}};`,
};
for (const component of ['ReglasAcceso','Bitacora','ReportesOperacion','UsuariosCondominio']) {
  mocks['@/components/'+component] = 'exports.default=()=>null;exports.AutorizarVisita=()=>null;';
}
function bundle(name, parent=path.join(process.cwd(),'entry.js')) {
  const file = mocks[name] ? name : require.resolve(name, {paths:[path.dirname(parent)]});
  if(ids.has(file)) return ids.get(file);
  const id=modules.length; ids.set(file,id); modules.push('');
  let source=mocks[name] || fs.readFileSync(file,'utf8');
  if(/\.tsx?$/.test(file)) source=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText;
  source=source.replace(/process\.env\.NODE_ENV/g,'"production"').replace(/require\(["']([^"']+)["']\)/g,(_,dep)=>`require(${bundle(dep,file)})`);
  modules[id]=`function(require,module,exports){${source}\n}`;
  return id;
}
(async()=>{
  const react=bundle('react'), dom=bundle('react-dom/client');
  const component=bundle(path.join(process.cwd(),'src/app/dashboard/admin/AdminClient.tsx'));
  const script=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}require(${dom}).createRoot(document.getElementById('root')).render(require(${react}).createElement(require(${component}).default));`;
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({viewport:{width:390,height:844}});
    await page.route('**/*', route=>route.fulfill({contentType:'text/html',body:'<div id="root"></div>'}));
    await page.goto('http://127.0.0.1:47892/');
    await page.evaluate(()=>{window.calls=[];window.mode='empty';localStorage.setItem('axs_condominio_id','stale');});
    await page.addScriptTag({content:script});
    await page.getByText('Cargando condominios…',{exact:true}).waitFor();
    assert.equal(await page.getByText('Sin condominios asignados',{exact:true}).count(),0);
    await page.waitForFunction(()=>typeof window.finish==='function');
    await page.evaluate(()=>window.finish());
    await page.getByText('Sin condominios asignados',{exact:true}).waitFor();
    assert.equal(await page.getByLabel('Condominio').isDisabled(),true);
    assert.deepEqual(await page.evaluate(()=>window.calls),['/condominios/']);
    await page.evaluate(()=>{window.mode='error';window.finish=null;});
    await page.getByRole('button',{name:'Actualizar accesos'}).click();
    await page.waitForFunction(()=>typeof window.finish==='function');
    await page.evaluate(()=>window.finish());
    await page.getByRole('alert').waitFor();
    assert.equal(await page.getByText('Sin condominios asignados',{exact:true}).count(),0);
    await page.evaluate(()=>{window.mode='success';window.finish=null;});
    await page.getByRole('button',{name:'Reintentar'}).click();
    await page.waitForFunction(()=>typeof window.finish==='function');
    await page.evaluate(()=>window.finish());
    await page.waitForFunction(()=>document.querySelector('select').value==='a');
    assert.equal(await page.getByLabel('Condominio').isDisabled(),false);
    assert.equal(await page.getByRole('alert').count(),0);
    assert.equal(await page.getByText('Sin condominios asignados',{exact:true}).count(),0);
    assert.ok((await page.evaluate(()=>window.calls)).includes('/visitas/condominio/a'));
    console.log('PASS: loading, empty access, no tenant calls, error, retry, stale selection recovery.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
