const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');const modules=[],ids=new Map();
const mocks={
'@clerk/nextjs':`const getToken=async()=>'synthetic';exports.useAuth=()=>({getToken});`,
'next/link':`exports.default=({children,...p})=>require('react').createElement('a',p,children);`,
'@/lib/api':`class ApiError extends Error{constructor(m,s){super(m);this.status=s}}exports.ApiError=ApiError;exports.api={get:async p=>{if(p==='/condominios/')return [{condominio_id:'a',nombre:'A'},{condominio_id:'b',nombre:'B'}];if(p.startsWith('/arco/b'))throw new ApiError('Sin designación',403);return window.rows;},post:async(p,b)=>{window.writes.push(b);if(p.endsWith('/estado'))window.rows[0]={...window.rows[0],state:b.state,version:2};else window.rows=[{...b,case_id:b.request_id,state:'recibida',version:1,pending_actions:0,history:[]}];return window.rows[0]}};`
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
const react=bundle('react'),dom=bundle('react-dom/client'),component=bundle(path.join(process.cwd(),'src/app/dashboard/arco/ArcoClient.tsx'));
const script=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}require(${dom}).createRoot(document.getElementById('root')).render(require(${react}).createElement(require(${component}).default));`;
const browser=await chromium.launch({headless:true});try{
 const page=await browser.newPage({viewport:{width:390,height:844}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent('<div id="root"></div>');await page.evaluate(()=>{window.rows=[];window.writes=[];if(!crypto.randomUUID)crypto.randomUUID=()=> '00000000-0000-4000-8000-000000000001';});await page.addScriptTag({content:script});await page.getByRole('heading',{name:'Solicitudes ARCO',exact:true}).waitFor();assert.deepEqual(errors,[]);
 await page.getByLabel('Cliente',{exact:true}).selectOption('b');await page.getByRole('alert').waitFor();assert.equal(await page.getByRole('button',{name:'Registrar solicitud',exact:true}).count(),0);
 await page.getByLabel('Cliente',{exact:true}).selectOption('a');
 for(const [label,value] of [['Referencia privada del titular','SYNTHETIC_001'],['Responsable asignado','Operador'],['Recepción original','2026-01-01T09:00'],['Vencimiento de determinación','2026-01-20T09:00']])await page.getByLabel(label).fill(value);
 await page.getByRole('button',{name:'Registrar solicitud',exact:true}).click();await page.getByRole('button',{name:'Ver seguimiento',exact:true}).click();await page.getByLabel('Referencia de evidencia').fill('VERIFICATION');await page.getByRole('button',{name:'Confirmar avance',exact:true}).click();await page.getByText('acceso · verificada · Pendientes: 0',{exact:true}).waitFor();assert.equal(await page.evaluate(()=>window.writes.length),2);
 await page.getByLabel('Cliente',{exact:true}).selectOption('b');await page.getByRole('alert').waitFor();assert.equal(await page.getByText(/Folio:/).count(),0);assert.deepEqual(errors,[]);console.log('PASS ARCO private forms, create, verify and tenant switch');
}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
