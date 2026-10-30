const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');const modules=[],ids=new Map();
const mocks={
'@clerk/nextjs':`const getToken=async()=>'synthetic';exports.useAuth=()=>({getToken,userId:window.__user,sessionId:window.__session});`,
'next/link':`exports.default=({children,...p})=>require('react').createElement('a',p,children);`,
'@/lib/api':`class ApiError extends Error{constructor(m,s){super(m);this.status=s}}exports.ApiError=ApiError;exports.api={
 get:async p=>{window.reads.push(p);if(p==='/arco-clientes'){if(window.clientDisabled)throw new ApiError('Disabled',404);return structuredClone(window.clients)}
 if(!p.startsWith('/arco/'))throw Error('Unexpected GET '+p);const tenant=p.split('/')[2].split('?')[0];
 if(tenant==='b')throw new ApiError('Sin designación vigente',403);
 if(tenant==='a'&&window.delayA)return new Promise(resolve=>window.resolveA=resolve);
 return structuredClone(window.rows[tenant]||[]);},
 post:async(p,b)=>{const tenant=p.split('/')[2];window.writes.push({p,b});
 if(p.endsWith('/estado'))window.rows[tenant][0]={...window.rows[tenant][0],state:b.state,version:2};
 else window.rows[tenant]=[{...b,case_id:b.request_id,state:'recibida',version:1,pending_actions:0,history:[]}];
 return structuredClone(window.rows[tenant][0]);}};`
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
const script=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}const root=require(${dom}).createRoot(document.getElementById('root'));window.renderArco=()=>root.render(require(${react}).createElement(require(${component}).default));window.renderArco();`;
const browser=await chromium.launch({headless:true});try{
 const page=await browser.newPage({viewport:{width:390,height:844}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>route.abort());
 await page.setContent('<div id="root"></div>');
 await page.evaluate(()=>{window.__user='privacy';window.__session='session1';window.rows={a:[],corp:[]};window.writes=[];window.reads=[];
 window.clients=[{tenant_id:'a',nombre:'Residencial A',modalidad:'residencial'},{tenant_id:'corp',nombre:'Empresa de prueba',modalidad:'corporativo'},{tenant_id:'b',nombre:'Permiso revocado',modalidad:'corporativo'}];
 if(!crypto.randomUUID)crypto.randomUUID=()=> '00000000-0000-4000-8000-000000000001';});
 await page.addScriptTag({content:script});await page.getByRole('heading',{name:'Solicitudes ARCO',exact:true}).waitFor();
 assert.deepEqual(errors,[]);
 await page.getByLabel('Cliente',{exact:true}).selectOption('b');await page.getByRole('alert').waitFor();assert.equal(await page.getByRole('button',{name:'Registrar solicitud',exact:true}).count(),0);
 await page.getByLabel('Cliente',{exact:true}).selectOption('corp');
 for(const [label,value] of [['Referencia privada del titular','CORP_SYNTHETIC'],['Responsable asignado','Operador'],['Recepción original','2026-01-01T09:00'],['Vencimiento de determinación','2026-01-20T09:00']])await page.getByLabel(label).fill(value);
 await page.getByRole('button',{name:'Registrar solicitud',exact:true}).click();await page.getByRole('button',{name:'Ver seguimiento',exact:true}).click();await page.getByLabel('Referencia de evidencia').fill('VERIFICATION');await page.getByRole('button',{name:'Confirmar avance',exact:true}).click();await page.getByText('acceso · verificada · Pendientes: 0',{exact:true}).waitFor();
 assert.equal(await page.evaluate(()=>window.writes.length),2);
 assert.ok((await page.evaluate(()=>window.writes)).every(call=>call.p.startsWith('/arco/corp')));
 assert.ok(!(await page.evaluate(()=>window.reads)).includes('/condominios/'));
 await page.evaluate(()=>window.delayA=true);
 await page.getByLabel('Cliente',{exact:true}).selectOption('a');await page.waitForFunction(()=>typeof window.resolveA==='function');
 await page.getByLabel('Cliente',{exact:true}).selectOption('corp');await page.getByText(/Titular: CORP_SYNTHETIC/).waitFor();
 await page.evaluate(async()=>{window.resolveA([{...window.rows.corp[0],subject_ref:'STALE_OTHER_CLIENT'}]);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));});
 assert.equal(await page.getByText(/STALE_OTHER_CLIENT/).count(),0);
 await page.evaluate(()=>{window.clients=[];window.__user='another-operator';window.__session='session2';window.renderArco();});
 await page.getByRole('status').getByText(/No tienes clientes/).waitFor();assert.equal(await page.getByText(/Folio:/).count(),0);
 assert.equal(await page.getByRole('button',{name:'Registrar solicitud',exact:true}).count(),0);
 await page.evaluate(()=>{window.clientDisabled=true;window.__session='session3';window.renderArco();});
 await page.getByRole('alert').getByText(/El registro ARCO no está habilitado/).waitFor();
 assert.equal(await page.getByRole('button',{name:'Registrar solicitud',exact:true}).count(),0);
 assert.deepEqual(errors,[]);console.log('PASS ARCO company selection, scoped writes, revocation, stale response and session isolation');
}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
