const fs = require('fs'), path = require('path'), ts = require('typescript');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const modules = [], ids = new Map();
const mocks = {
  'next/navigation': `exports.useRouter=()=>({push:()=>{}});`,
  '@clerk/nextjs': `const getToken=async()=>'synthetic';exports.useAuth=()=>({getToken});`,
  '@/lib/api': `const residents=[{usuario_id:'one',nombre:'Ana',email:'ana@example.test',rol:'RESIDENTE'}];exports.api={get:async p=>p==='/condominios/'?[{condominio_id:'a',nombre:'Condominio A'}]:p.endsWith('/casas')?{total_casas:1,casas:[{casa_id:'home',numero:'101',tipo:'casa',residente:residents[0],residentes:[...residents]}]}:[],post:async(p,body)=>{window.saved={p,body};residents.push({usuario_id:'two',rol:'RESIDENTE',...body});}};`,
};
for (const component of ['ReglasAcceso','Bitacora','ReportesOperacion','UsuariosCondominio']) {
  mocks['@/components/'+component] = 'exports.default=()=>null;exports.AutorizarVisita=()=>null;';
}
function bundle(name, parent=path.join(process.cwd(),'entry.js')) {
  const alias = name.startsWith('@/') ? path.join(process.cwd(), 'src', name.slice(2)) : null;
  const local = alias && ['.tsx', '.ts', '.js'].map(ext => alias + ext).find(file => fs.existsSync(file));
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
  const react=bundle('react'), dom=bundle('react-dom/client');
  const component=bundle(path.join(process.cwd(),'src/app/dashboard/admin/AdminClient.tsx'));
  const script=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}require(${dom}).createRoot(document.getElementById('root')).render(require(${react}).createElement(require(${component}).default));`;
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({viewport:{width:390,height:844}});
    await page.route('**/*', route=>route.fulfill({contentType:'text/html',body:'<div id="root"></div>'}));
    await page.goto('http://127.0.0.1:47892/');
    await page.addScriptTag({content:script});
    await page.getByRole('button',{name:'Viviendas / Destinos',exact:true}).click();
    await page.getByText('ana@example.test',{exact:true}).waitFor();
    await page.getByRole('button',{name:'+ Agregar residente',exact:true}).click();
    await page.getByPlaceholder('Nombre del residente').fill('Luis');
    await page.getByPlaceholder('Email *',{exact:true}).fill('luis@example.test');
    await page.getByRole('button',{name:'Asignar',exact:true}).click();
    await page.getByText('luis@example.test',{exact:true}).waitFor();
    assert.equal(await page.getByText('ana@example.test',{exact:true}).count(),1);
    assert.equal(await page.getByRole('button',{name:'+ Agregar residente',exact:true}).count(),1);
    assert.deepEqual(await page.evaluate(()=>window.saved),{p:'/condominios/a/casas/home/residente',body:{nombre:'Luis',email:'luis@example.test'}});
    await page.getByRole('button',{name:'Usuarios',exact:true}).click();
    await page.getByRole('button',{name:'Viviendas / Destinos',exact:true}).click();
    await page.getByText('ana@example.test',{exact:true}).waitFor();
    await page.getByText('luis@example.test',{exact:true}).waitFor();
    console.log('PASS: add a second resident, retain both, reload list and keep add available.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
