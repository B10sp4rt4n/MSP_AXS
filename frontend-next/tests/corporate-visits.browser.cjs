// Synthetic browser rehearsal. No external API, Clerk, database or account is contacted.
const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const modules=[],ids=new Map();
const mocks={
 '@clerk/nextjs': `const getToken=async()=>{if(window.__holdToken)await new Promise(r=>window.__tokenWaits.push(r));return window.__session?'synthetic':null};
 exports.useAuth=()=>({getToken,isLoaded:true,userId:window.__session?'fixture':null});`,
 '@/lib/api': `exports.api={get:async(p,t,signal)=>{
 window.__reads.push(p); if(window.__deny)throw Error('denied');
 if(p.includes('/corp_other/'))throw Error('foreign company');
 if(signal?.aborted)throw Error('aborted');
 if(p.endsWith('/capacidades'))return {hosts:[{user_id:'host',nombre:'Anfitrion'}],can_authorize:window.__role!=='reception',can_record_movement:window.__role!=='host'};
 if(p.endsWith('/destinos'))return [{destination_id:'d1',nombre:'Recepcion'}];
 if(p.endsWith('/bitacora'))return window.__events.map((a,i)=>({action:a,event_uid:String(i),timestamp:'2026-11-15T00:00:00'}));
 return structuredClone(window.__visits);
 },post:async(p,b)=>{window.__writes.push({p,b});
 const found=window.__visits.find(v=>v.visit_id===b.request_id);if(found)return found;
 const row={...b,visit_id:b.request_id,state:'preregistrada',created_at:'2026-11-15T00:00:00'};
 window.__visits.push(row);window.__events.push('preregistrar');
 if(window.__lost){window.__lost=false;throw Error('lost ACK')}return row;
 },patch:async(p)=>{window.__patches.push(p);const action=p.split('/').at(-1),row=window.__visits[0];
 row.state={autorizar:'autorizada',entrada:'dentro',salida:'cerrada',cancelar:'cancelada'}[action];
 window.__events.push(action);return structuredClone(row);}};`
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
 const comp=bundle(path.join(process.cwd(),'src/app/dashboard/corporativo/visitas/CorporateVisitsClient.tsx'));
 const js=`const mods=[${modules.join(',')}],cache={};
 function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}
 window.__mount=(tenant='corp_fixture')=>{window.__root?.unmount();window.__root=require(${dom}).createRoot(document.getElementById('root'));window.__root.render(require(${react}).createElement(require(${comp}).default,{tenant,site:'site_fixture'}))};window.__mount();`;
 const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{})});
 try{
  const page=await browser.newPage({viewport:{width:360,height:800}});
  await page.setContent('<div id="root"></div>');
  await page.evaluate(()=>{if(!crypto.randomUUID){let id=0;Object.defineProperty(crypto,'randomUUID',{value:()=> '00000000-0000-4000-8000-'+String(++id).padStart(12,'0')})};window.__session=true;window.__role='owner';window.__reads=[];window.__writes=[];window.__patches=[];window.__visits=[];window.__events=[];window.__lost=true;window.__deny=false});
  await page.addScriptTag({content:js});
  await page.getByLabel('Referencia de visita').fill('INVALID REF');
  assert.equal(await page.getByLabel('Referencia de visita').evaluate(input=>input.checkValidity()),false);
  await page.getByLabel('Referencia de visita').fill('FOLIO-TEST');
  assert.equal(await page.getByLabel('Referencia de visita').evaluate(input=>input.checkValidity()),true);
  await page.getByLabel('Referencia de visita').fill('FOLIO_TEST');
  await page.getByLabel('Anfitrión',{exact:true}).selectOption('host');
  await page.getByLabel('Destino',{exact:true}).selectOption('d1');
  await page.locator('form').evaluate(form=>{for(let i=0;i<2;i++)form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))});
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByRole('button',{name:'Registrar entrada',exact:true}).count(),0);
  await page.getByRole('button',{name:'Reintentar misma solicitud',exact:true}).click();
  await page.getByRole('heading',{name:'FOLIO_TEST',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.__visits.length),1);
  assert.equal(await page.evaluate(()=>window.__writes[0].b.request_id===window.__writes[1].b.request_id),true);
  for(const action of ['Autorizar','Registrar entrada','Registrar salida']){
   const before=await page.evaluate(()=>window.__patches.length);
   await page.getByRole('button',{name:action,exact:true}).click();
   await page.getByRole('dialog').waitFor();
   assert.equal(await page.evaluate(()=>window.__patches.length),before);
   await page.getByRole('button',{name:'Confirmar',exact:true}).click();
   await page.waitForFunction(n=>window.__patches.length===n,before+1);
  }
  await page.getByText('Salida registrada',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Ver bitácora de FOLIO_TEST',exact:true}).click();
  await page.getByRole('region',{name:'Bitácora de visita'}).waitFor();
  assert.deepEqual(await page.evaluate(()=>window.__events),['preregistrar','autorizar','entrada','salida']);
  await page.evaluate(()=>{window.__role='host';window.__visits[0].state='autorizada';window.__mount()});
  await page.getByRole('heading',{name:'FOLIO_TEST',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Registrar entrada',exact:true}).count(),0);
  await page.getByLabel('Referencia de visita').fill('OLD_CONTEXT');
  await page.getByLabel('Anfitrión',{exact:true}).selectOption('host');
  await page.getByLabel('Destino',{exact:true}).selectOption('d1');
  const writesBefore=await page.evaluate(()=>window.__writes.length);
  await page.evaluate(()=>{window.__holdToken=true;window.__tokenWaits=[]});
  await page.getByRole('button',{name:'Crear preregistro',exact:true}).click();
  await page.waitForFunction(()=>window.__tokenWaits.length>0);
  await page.evaluate(()=>{window.__mount('corp_other');window.__holdToken=false;for(const release of window.__tokenWaits)release()});
  await page.getByRole('alert').waitFor();
  assert.equal(await page.evaluate(()=>window.__writes.length),writesBefore);
  await page.evaluate(()=>{window.__deny=true;window.__mount()});
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByRole('button',{name:'Crear preregistro',exact:true}).count(),0);
  await page.evaluate(()=>{window.__deny=false;window.__mount('corp_other')});
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByText('FOLIO_TEST',{exact:true}).count(),0);
  const reads=await page.evaluate(()=>window.__reads.length);
  await page.evaluate(()=>{window.__session=false;window.__mount()});
  await page.getByText('Inicia sesión para continuar.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.__reads.length),reads);
  console.log('PASS corporate visits: lost ACK stable UUID, explicit review, complete cycle, audit, host permissions, denial, company switch, pending-token scope change and signed-out gate. Synthetic only.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
