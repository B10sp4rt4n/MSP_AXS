const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const modules=[],ids=new Map();
const mocks={
 '@clerk/nextjs':`const getToken=async()=>'synthetic';exports.useAuth=()=>({getToken});`,
 '@/lib/api':`class ApiError extends Error { constructor(m,s){super(m);this.status=s;} } exports.ApiError=ApiError;
 exports.api={get:async p=>{if(window.offline)throw Error('Failed to fetch');
   if(p.split('/').length===4){const row=window.rows.find(r=>r.solicitud_id===p.split('/')[3]);if(!row)throw new ApiError('No encontrada',404);return {...row};}
   return window.rows.map(r=>({...r}));},
 post:async(p,data)=>{window.posts.push(data);
  if(p.endsWith('/respuesta')){const row=window.rows.find(r=>p.includes(r.solicitud_id));row.estado=data.decision; if(window.loseReply){window.offline=true;throw Error('Failed to fetch');} return {...row};}
  let row=window.rows.find(r=>r.solicitud_id===data.solicitud_id);
  if(!row){row={...data,visita_id:'visit',casa_unidad:'101',estado:'pendiente',entrada_registrada:false,expira_en:new Date(Date.now()+300000).toISOString()};window.rows.push(row);}
  if(window.loseCreate){window.loseCreate=false;window.offline=true;throw Error('Failed to fetch');}return {...row};}};`
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
 const react=bundle('react'),dom=bundle('react-dom/client'),component=bundle(path.join(process.cwd(),'src/components/SolicitudesAcceso.tsx'));
 const script=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}require(${dom}).createRoot(document.getElementById('root')).render(require(${react}).createElement(require(${component}).default,window.props));`;
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>r.fulfill({contentType:'text/html',body:'<div id="root"></div>'}));
  async function open(residente,estado='pendiente') {
   await page.goto('http://127.0.0.1:47894/');
   await page.evaluate(({residente,estado})=>{
    window.posts=[];window.offline=false;window.loseCreate=false;window.loseReply=false;
    window.props={condominioId:'a',...(residente?{residente:true}:{destinoId:'home'})};
    window.rows=residente?[{solicitud_id:'test',visita_id:'visit',destino_id:'home',casa_unidad:'101',nombre_visitante:'Ana Pérez',proposito:'Entrega',estado,expira_en:new Date(Date.now()+300000).toISOString(),entrada_registrada:false}]:[];
   },{residente,estado});
   await page.addScriptTag({content:script});
  }
  await open(false);
  await page.getByRole('button',{name:'Solicitar autorización sin QR',exact:true}).click();
  await page.getByLabel('Nombre completo del visitante').fill('Ana Pérez');
  await page.getByLabel('Motivo de la visita').fill('Entrega');
  await page.evaluate(()=>window.loseCreate=true);
  await page.getByRole('button',{name:'Pedir decisión al residente',exact:true}).click();
  await page.getByRole('button',{name:'Recuperar o reintentar solicitud',exact:true}).waitFor();
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByLabel('Nombre completo del visitante').isDisabled(),true);
  await page.evaluate(()=>window.offline=false);
  await page.getByRole('button',{name:'Recuperar o reintentar solicitud',exact:true}).click();
  await page.getByText('Esperando la decisión del residente. Aún no permitas la entrada.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.rows.length),1);
  assert.equal(await page.evaluate(()=>window.posts[0].solicitud_id===window.posts[1].solicitud_id),true);
  assert.equal(await page.evaluate(()=>window.rows[0].destino_id),'home');
  await open(true);
  await page.getByRole('button',{name:'Permitir entrada',exact:true}).click();
  assert.equal(await page.evaluate(()=>window.posts.length),0);
  await page.evaluate(()=>window.loseReply=true);
  await page.getByRole('button',{name:'Confirmar permiso',exact:true}).click();
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByRole('button',{name:'Permitir entrada',exact:true}).count(),0);
  await page.evaluate(()=>window.offline=false);
  await page.getByRole('button',{name:'Actualizar solicitudes',exact:true}).click();
  await page.getByText('El residente permitió el acceso. Falta confirmar la entrada en caseta.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.posts.length),1);
  assert.equal(await page.evaluate(()=>window.posts[0].consentimiento),true);
  assert.equal(await page.evaluate(()=>window.rows[0].entrada_registrada),false);
  await open(true);
  await page.getByRole('button',{name:'Rechazar entrada',exact:true}).click();
  await page.getByRole('button',{name:'Confirmar rechazo',exact:true}).click();
  await page.getByText('El residente rechazó el acceso. No permitas la entrada.',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Permitir entrada',exact:true}).count(),0);
  await open(true,'expirada');
  await page.getByText('La solicitud venció. No hay permiso vigente para entrar.',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Permitir entrada',exact:true}).count(),0);
  // A completed entry must disappear from the guard inbox on its next poll,
  // including a stale authorization state with a confirmed entry flag.
  for (const estado of ['consumida', 'permitida']) {
   await open(false);
   await page.evaluate(()=>window.rows=[{solicitud_id:'closed',visita_id:'left',destino_id:'home',casa_unidad:'101',nombre_visitante:'Visita que salió',proposito:'Entrega',estado:'pendiente',expira_en:new Date(Date.now()+300000).toISOString(),entrada_registrada:false}]);
   await page.getByRole('button',{name:'Actualizar solicitudes',exact:true}).click();
   await page.getByText('Visita que salió · 101',{exact:true}).waitFor();
   await page.evaluate(estado=>{window.rows[0].estado=estado;window.rows[0].entrada_registrada=true;},estado);
   await page.getByText('Visita que salió · 101',{exact:true}).waitFor({state:'detached',timeout:10000});
   await page.getByText('No hay solicitudes para mostrar.',{exact:true}).waitFor();
   assert.equal(await page.evaluate(()=>window.rows.length),1);
   assert.equal(await page.evaluate(()=>window.posts.length),0);
  }
  // A resident sees an entered visitor only until the exit is recorded.
  await open(true,'consumida');
  await page.getByText('Entrada registrada en caseta.',{exact:true}).waitFor();
  await page.evaluate(()=>{window.rows[0].salida_registrada=true;});
  await page.getByText('Entrada registrada en caseta.',{exact:true}).waitFor({state:'detached',timeout:10000});
  await page.getByText('No hay solicitudes para mostrar.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.rows.length),1);
  assert.equal(await page.evaluate(()=>window.posts.length),0);
  assert.deepEqual(errors,[]);
  console.log('PASS remote app: lost create/reply, stable ID/destination, explicit consent, rejection, expiry, no automatic entry');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
