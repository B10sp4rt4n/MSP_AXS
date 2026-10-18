const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const modules=[],ids=new Map();
const mocks={
 '@clerk/nextjs':`const getToken=async()=>'synthetic';exports.useAuth=()=>({getToken});`,
 '@/lib/api':`const copy=()=>JSON.parse(JSON.stringify(window.profile));exports.api={
 get:async()=>copy(),
 patch:async(p,b)=>{window.calls.push(b);if(window.fail)throw Error('No se pudo guardar');window.profile.celular=b.celular;return copy()},
 put:async(p,b)=>{window.calls.push(b);const provider=p.split('/').pop();window.profile.identities=[{provider,reference:b.reference,verified_at:null,revoked_at:null}];return copy()},
 delete:async()=>{window.profile.identities=[];return copy()}};`
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
 const react=bundle('react'),dom=bundle('react-dom/client'),component=bundle(path.join(process.cwd(),'src/components/IdentityProfile.tsx'));
 const script=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}require(${dom}).createRoot(document.getElementById('root')).render(require(${react}).createElement(require(${component}).default));`;
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setContent('<div id="root"></div>');
  await page.evaluate(()=>{window.profile={usuario_id:'same-person',celular:null,identities:[]};window.calls=[];});
  await page.addScriptTag({content:script});
  await page.getByLabel('Celular (opcional)',{exact:true}).fill('+525512345678');
  const save=page.getByRole('button',{name:'Guardar Celular',exact:true});
  assert.equal(await save.isDisabled(),true);
  await page.locator('form').nth(0).getByRole('checkbox').check();
  await page.evaluate(()=>window.fail=true);
  await save.click();
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByLabel('Celular (opcional)',{exact:true}).inputValue(),'+525512345678');
  await page.evaluate(()=>window.fail=false);
  await page.locator('form').nth(0).getByRole('checkbox').check();
  await save.click();
  await page.getByRole('button',{name:'Retirar Celular',exact:true}).waitFor();
  await page.getByLabel('Facebook (opcional)',{exact:true}).fill('https://facebook.com/person');
  await page.locator('form').nth(2).getByRole('checkbox').check();
  await page.getByRole('button',{name:'Guardar Facebook',exact:true}).click();
  await page.getByRole('button',{name:'Retirar Facebook',exact:true}).click();
  await page.getByText('Dato retirado y autorización revocada.',{exact:true}).waitFor();
  assert.equal(await page.getByLabel('Facebook (opcional)',{exact:true}).inputValue(),'');
  assert.equal(await page.evaluate(()=>window.profile.usuario_id),'same-person');
  assert.deepEqual(errors,[]);
  console.log('PASS progressive profile: optional fields, explicit consent, failed save, retry, revoke');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
