// Synthetic browser rehearsal. No external API, Clerk, database or account is contacted.
const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const modules=[],ids=new Map();
const mocks={
 '@clerk/nextjs': `const getToken=async()=>window.__session?'synthetic':null;
 exports.UserButton=()=>null;
 exports.useAuth=()=>({getToken,isLoaded:true,userId:window.__session?'owner-fixture':null});`,
 '@/lib/api': `class ApiError extends Error{constructor(message,status){super(message);this.status=status}};
 exports.ApiError=ApiError;
 exports.api={get:async(p,t,signal)=>{
  window.__reads.push(p);
  if(window.__hold){await new Promise(r=>window.__release=r)}
  if(signal?.aborted)throw Error('aborted');
  if(window.__deny)throw new ApiError('Sin membresía',403);
  if(p.includes('/corp_other/'))throw new ApiError('Otra empresa',403);
  if(p.endsWith('/destinos'))return structuredClone(window.__destinations[p.split('/')[4]]||[]);
  return structuredClone(window.__sites);
 },post:async(p,b)=>{
  window.__writes.push({p,b});
  if(window.__deny)throw new ApiError('Sin membresía',403);
  if(window.__quota)throw new ApiError('Capacidad corporativa restringida por gobierno',403);
  if(p.endsWith('/sedes')){
   const row={site_id:'site_'+(window.__sites.length+1),tenant_id:'corp_fixture',nombre:b.nombre,zona_horaria:b.zona_horaria,activa:true};
   window.__sites.push(row);
   if(window.__unknown){window.__unknown=false;throw Error('ACK perdido')}
   return structuredClone(row);
  }
  const site=p.split('/')[4];
  const row={destination_id:'area_'+(window.__writes.length),tenant_id:'corp_fixture',site_id:site,nombre:b.nombre,activa:true};
  (window.__destinations[site]||=[]).push(row);
  return structuredClone(row);
 }};`
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
 const comp=bundle(path.join(process.cwd(),'src/app/dashboard/corporativo/CorporateDirectoryClient.tsx'));
 const js=`const mods=[${modules.join(',')}],cache={};
 function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}
 window.__mount=(tenant='corp_fixture')=>{window.__root?.unmount(); window.__root=require(${dom}).createRoot(document.getElementById('root')); window.__root.render(require(${react}).createElement(require(${comp}).default,{initialTenant:tenant}));};window.__mount();`;
 const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{})});
 try {
  const page=await browser.newPage({viewport:{width:360,height:800}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>route.request().url()==='http://127.0.0.1:47892/'?
    route.fulfill({contentType:'text/html',body:'<meta name="viewport" content="width=device-width, initial-scale=1"><div id="root"></div>'}):route.abort());
  await page.goto('http://127.0.0.1:47892/');
  const css=await require('postcss')([require('@tailwindcss/postcss')()]).process('@import "tailwindcss";', {from:path.join(process.cwd(),'src/app/globals.css')});
  await page.addStyleTag({content:css.css});
  await page.evaluate(()=>Object.assign(window,{__session:true,__deny:true,__reads:[],__writes:[],__sites:[],__destinations:{},__quota:false,__unknown:false,__hold:false}));
  await page.addScriptTag({content:js});
  const click=name=>page.getByRole('button',{name,exact:true}).click();
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByRole('button',{name:'Crear sede',exact:true}).count(),0,'Denied membership cannot mount directory');
  assert.equal(await page.evaluate(()=>window.__writes.length),0);
  await page.evaluate(()=>window.__deny=false);
  await click('Consultar estado del directorio');
  await page.getByText('Todavía no hay sedes. Crea la primera.',{exact:true}).waitFor();
  await page.getByLabel('Nombre de sede').fill('Oficina de ensayo');
  await click('Crear sede');
  await page.getByText('Sede creada: Oficina de ensayo',{exact:true}).waitFor();
  await page.getByLabel('Nombre del destino').fill('Recepción');
  await click('Crear destino');
  await page.getByText('Destino creado: Recepción',{exact:true}).waitFor();
  assert.equal(await page.getByRole('listitem').textContent(),'Recepción');
  await page.getByRole('button',{name:'Oficina de ensayo America/Mexico_City',exact:true}).click();
  assert.equal(await page.getByRole('listitem').textContent(),'Recepción','Reselecting current site preserves its destinations');
  await page.getByLabel('Nombre de sede').fill('Sucursal de ensayo');
  await click('Crear sede');
  await page.getByText('Esta sede todavía no tiene destinos.',{exact:true}).waitFor();
  assert.equal(await page.getByRole('listitem').count(),0,'Destinations never cross sites');
  await page.getByLabel('Nombre del destino').fill('Administración');
  await click('Crear destino');
  await page.getByText('Destino creado: Administración',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Oficina de ensayo America/Mexico_City',exact:true}).click();
  await page.getByRole('listitem').getByText('Recepción',{exact:true}).waitFor();
  assert.equal(await page.getByRole('listitem').count(),1);
  // Unknown POST result: one write, blocked resubmission, read-back finds committed row.
  await page.evaluate(()=>window.__unknown=true);
  await page.getByLabel('Nombre de sede').fill('Sede con ACK perdido');
  await click('Crear sede');
  await page.getByText(/El alta pudo haberse guardado/).waitFor();
  assert.equal(await page.getByRole('button',{name:'Crear sede',exact:true}).isDisabled(),true);
  const writes=await page.evaluate(()=>window.__writes.length);
  await click('Consultar estado del directorio');
  await page.getByRole('button',{name:'Sede con ACK perdido America/Mexico_City',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.__writes.length),writes,'Read-back must never resend POST');
  // Quota denial remains visible and does not claim success or expose stale lists.
  await page.evaluate(()=>window.__quota=true);
  await page.getByLabel('Nombre de sede').fill('Sede excedente');
  await click('Crear sede');
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByRole('button',{name:'Crear sede',exact:true}).count(),0);
  assert.equal(await page.evaluate(()=>window.__sites.length),3);
  await page.evaluate(()=>{window.__quota=false;window.__mount();});
  await page.getByRole('button',{name:'Oficina de ensayo America/Mexico_City',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.__sites.length),3,'Remount reads persisted state without writes');
  // Delayed read from the old company cannot appear after switching companies.
  await page.evaluate(()=>window.__hold=true);
  await click('Consultar estado del directorio');
  await page.waitForFunction(()=>typeof window.__release==='function');
  await page.getByLabel('Identificador de empresa').fill('corp_other');
  await page.evaluate(()=>window.__hold=false);
  await click('Abrir directorio');
  await page.getByRole('alert').waitFor();
  await page.evaluate(()=>window.__release());
  assert.equal(await page.getByRole('button',{name:'Oficina de ensayo America/Mexico_City',exact:true}).count(),0);
  assert.equal(await page.getByRole('button',{name:'Crear sede',exact:true}).count(),0);
  assert.match(page.url(),/empresa=corp_other/);
  // Signing out remounts without directory data or requests.
  const reads=await page.evaluate(()=>window.__reads.length);
  await page.evaluate(()=>{window.__session=false;window.__mount();});
  await page.getByText('Inicia sesión para consultar tu directorio.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.__reads.length),reads);
  assert.equal(await page.getByRole('button',{name:'Crear sede',exact:true}).count(),0);
  await page.evaluate(()=>{window.__session=true;window.__mount();});
  await page.getByRole('button',{name:'Oficina de ensayo America/Mexico_City',exact:true}).waitFor();
  for(const width of [320,360,1280]){
    await page.setViewportSize({width,height:900});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'Overflow at '+width);
    if(process.env.AXS_SCREENSHOT_DIR){fs.mkdirSync(process.env.AXS_SCREENSHOT_DIR,{recursive:true});await page.screenshot({path:path.join(process.env.AXS_SCREENSHOT_DIR,`corporate-directory-${width}.png`),fullPage:true});}
  }
  assert.deepEqual(errors,[],'No browser runtime errors');
  console.log('PASS: membership denial, site creation, destination isolation, reselect, uncertain POST/read-back, quota denial, remount, company switch/stale response, signed-out gate, 3 viewport widths');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
