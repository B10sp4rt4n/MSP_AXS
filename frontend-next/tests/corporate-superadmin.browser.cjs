// Browser rehearsal: all API/Clerk transport is synthetic and all external traffic blocked.
// This test never touches Railway, Vercel, Neon, or a real Clerk account.
const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const modules=[],ids=new Map();
const mocks={
 '@clerk/nextjs': `const getToken=async()=> 'synthetic-test-token';
exports.useAuth=()=>({getToken,isLoaded:true,userId:'global-fixture'});`,
 '@/lib/api': `class ApiError extends Error{constructor(message,status){super(message);this.status=status}}
exports.ApiError=ApiError;
exports.api={
  get:async p=>{
    window.__reads.push(p);
    if(window.__deny)throw new ApiError('No autorizado',403);
    if(window.__disabled)throw new ApiError('Off',404);
    if(p==='/plataforma/corporativo/acceso')return {authorized:true,provisioning_enabled:true,credencial_configurada:true};
    if(p.startsWith('/plataforma/corporativo/usuarios/'))return {usuario_id:p.split('/').pop()};
    if(p.startsWith('/plataforma/corporativo/empresas/')){
      const company=Object.values(window.__companies).find(v=>v.tenant_id===p.split('/').pop());
      if(!company)throw new ApiError('Empresa ausente',404);
      const operation=company.capacidades_operacion,quotas=window.__capabilities;
      return {...structuredClone(company),
        capacidades:quotas?{max_sedes:quotas.max_sedes,max_destinos_por_sede:quotas.max_destinos_por_sede}:{max_sedes:null,max_destinos_por_sede:null},
        capacidades_confirmadas:!!(window.__govValid&&operation?.estado==='confirmed'&&quotas?.request_id===operation.request_id&&
          quotas.max_sedes===operation.max_sedes&&quotas.max_destinos_por_sede===operation.max_destinos_por_sede)};
    }
    throw Error('Unexpected GET '+p);
  },
  post:async(p,b)=>{
    window.__calls.push({method:'POST',p,b});
    if(p==='/plataforma/corporativo/empresas'){
      if(!window.__companies[b.request_id])window.__companies[b.request_id]={
        tenant_id:'corp_'+b.request_id.replaceAll('-',''),nombre:b.nombre,msp_id:b.msp_id,
        owner_user_id:b.owner_user_id,modalidad:'corporativo',directorio_habilitado:false,
        privacy_contact:b.privacy_contact,privacy_notice_version:b.privacy_notice_version,
        capacidades_operacion:null,capacidades_revision:0,capacidades_confirmadas:false};
      const row=window.__companies[b.request_id];
      if(row.nombre!==b.nombre)throw new ApiError('Referencia utilizada',409);
      if(window.__failOnce){window.__failOnce=false;throw new Error('ACK incierto tras commit')}
      return structuredClone(row);
    }
    if(p.endsWith('/habilitar-directorio')){
      if(b.confirmacion!==true)throw new ApiError('Confirmación obligatoria',422);
      const id=p.split('/')[4];
      const row=Object.values(window.__companies).find(v=>v.tenant_id===id);
      if(!row)throw new ApiError('Empresa no existe',404);
      if(row.capacidades_operacion?.estado!=='confirmed'||!window.__govValid||
        window.__capabilities?.request_id!==row.capacidades_operacion.request_id)
        throw new ApiError('Capacidades sin confirmar',409);
      row.directorio_habilitado=true;return structuredClone(row);
    }
    throw Error('Unexpected POST '+p);
  },
  put:async(p,b)=>{
    window.__calls.push({method:'PUT',p,b});
    if(!p.endsWith('/capacidades'))throw Error('Unexpected PUT '+p);
    if(!/^[0-9a-f-]{36}$/.test(b.request_id)||!Number.isInteger(b.expected_revision))
      throw new ApiError('UUID y revisión obligatorios',422);
    const tenant_id=p.split('/')[4],row=Object.values(window.__companies).find(v=>v.tenant_id===tenant_id);
    if(!row)throw new ApiError('Empresa no existe',404);
    if(window.__quotaConflictOnce){window.__quotaConflictOnce=false;throw new ApiError('Conflicto de configuración',409)}
    let operation=window.__capacityOperations[b.request_id];
    if(row.capacidades_operacion?.estado==='needs_review')throw new ApiError('Revisión requerida',409);
    if(operation){
      if(operation.expected_revision!==b.expected_revision||operation.max_sedes!==b.max_sedes||
        operation.max_destinos_por_sede!==b.max_destinos_por_sede)throw new ApiError('Referencia utilizada',409);
    }else{
      if(row.capacidades_operacion?.estado==='pending')throw new ApiError('Conciliación pendiente',409);
      if(row.capacidades_revision!==b.expected_revision)throw new ApiError('Revisión desactualizada',409);
      operation={...b,estado:'pending',revision:b.expected_revision+1};
      window.__capacityOperations[b.request_id]=operation;
      row.capacidades_revision=operation.revision;
    }
    row.capacidades_operacion=operation;
    window.__capabilities={request_id:b.request_id,max_sedes:b.max_sedes,max_destinos_por_sede:b.max_destinos_por_sede};
    window.__govValid=true;
    if(window.__quotaHold)throw new Error('ACK incierto de capacidades tras GOV');
    operation.estado='confirmed';
    if(window.__quotaAckLossOnce){window.__quotaAckLossOnce=false;throw new Error('ACK perdido de capacidades confirmadas')}
    return {tenant_id,request_id:b.request_id,estado:'confirmed',revision:operation.revision,
      cuotas:{max_sedes:b.max_sedes,max_destinos_por_sede:b.max_destinos_por_sede}};
  }
};`
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
 const comp=bundle(path.join(process.cwd(),'src/app/dashboard/corporativo-superadmin/CorporativoSuperadminClient.tsx'));
 const js=`const mods=[${modules.join(',')}],cache={};
 function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}
 require(${dom}).createRoot(document.getElementById('root')).render(
 require(${react}).createElement(require(${comp}).default));`;
 const browser=await chromium.launch({headless:true,
   ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{})});
 try{
  const page=await browser.newPage({viewport:{width:360,height:800}});
  const css=await require('postcss')([require('@tailwindcss/postcss')()]).process('@import "tailwindcss";', {from:path.join(process.cwd(),'src/app/globals.css')});
  await page.route('**/*',route=>route.request().url()==='http://127.0.0.1:47891/'?
    route.fulfill({contentType:'text/html',body:`<meta name="viewport" content="width=device-width, initial-scale=1"><style>${css.css}</style><div id="root"></div>`}):route.abort());
  await page.goto('http://127.0.0.1:47891/');
  await page.evaluate(()=>{window.__reads=[];window.__calls=[];window.__companies={};
    window.__capabilities=null;window.__capacityOperations={};window.__govValid=true;
    window.__quotaHold=false;window.__quotaAckLossOnce=false;window.__quotaConflictOnce=false;
    window.__deny=true;window.__disabled=false;window.__failOnce=false;});
  await page.addScriptTag({content:js});
  const click=name=>page.getByRole('button',{name,exact:true}).click();
  await page.getByRole('alert').getByText('Tu cuenta no tiene autoridad GLOBAL.').waitFor();
  assert.equal(await page.getByRole('button',{name:'Crear empresa deshabilitada'}).count(),0);
  assert.equal(await page.evaluate(()=>window.__calls.length),0);
  await page.evaluate(()=>window.__deny=false);
  await click('Reintentar comprobación');
  await page.getByRole('button',{name:'Crear empresa deshabilitada'}).waitFor();
  await page.getByLabel('Nombre de empresa').fill('Empresa Sintética');
  await page.getByLabel('ID del MSP responsable').fill('msp_synthetic');
  await page.getByLabel('ID del propietario inicial').fill('owner_synthetic');
  await page.getByLabel('Correo del responsable de privacidad').fill('privacidad@example.test');
  await page.getByLabel('URL HTTPS del aviso de privacidad').fill('https://example.test/aviso');
  await page.getByLabel('Versión del aviso').fill('2026-10');
  await click('Verificar owner existente');
  await page.getByText('Owner verificado: owner_synthetic').waitFor();
  await page.evaluate(()=>window.__failOnce=true);
  await click('Crear empresa deshabilitada');
  await page.getByRole('alert').getByText('ACK incierto tras commit').waitFor();
  const one=await page.evaluate(()=>window.__calls[0].b.request_id);
  assert.match(one,/^[0-9a-f-]{36}$/);
  assert.equal(await page.evaluate(()=>Object.keys(window.__companies).length),1);
  await click('Crear empresa deshabilitada');
  await page.getByText('Capacidades de directorio').waitFor();
  assert.equal(await page.evaluate(()=>window.__calls[1].b.request_id),one,'Retry must preserve UUID');
  assert.equal(await page.evaluate(()=>Object.keys(window.__companies).length),1);
  await page.getByLabel('Máximo de sedes').fill('2');
  await page.getByLabel('Destinos máximos por sede').fill('10');
  await page.evaluate(()=>window.__quotaHold=true);
  await click('Guardar capacidades');
  await page.getByRole('alert').getByText('ACK incierto de capacidades tras GOV').waitFor();
  const quotaRequest=await page.evaluate(()=>window.__calls.find(c=>c.method==='PUT').b);
  assert.match(quotaRequest.request_id,/^[0-9a-f-]{36}$/);
  assert.notEqual(quotaRequest.request_id,one,'Quota operation must have its own UUID');
  assert.equal(quotaRequest.expected_revision,0);
  const assertPending=async()=>{
    await page.getByRole('button',{name:'Reintentar conciliación',exact:true}).waitFor();
    assert.equal(await page.getByLabel('Máximo de sedes').isDisabled(),true);
    assert.equal(await page.getByLabel('Destinos máximos por sede').isDisabled(),true);
    assert.equal(await page.getByRole('button',{name:'Comenzar otra alta',exact:true}).isDisabled(),true);
    assert.equal(await page.getByText('Habilitación del directorio',{exact:true}).count(),0);
    assert.equal(await page.getByRole('button',{name:'Habilitar directorio',exact:true}).count(),0);
    assert.equal(await page.evaluate(()=>window.__calls.filter(c=>c.p.endsWith('/habilitar-directorio')).length),0);
  };
  await assertPending();
  await assert.rejects(page.getByLabel('Máximo de sedes').fill('999',{timeout:200}),/not enabled|Timeout/);
  assert.equal(await page.getByLabel('Máximo de sedes').inputValue(),'2');
  await click('Reintentar conciliación');
  await page.getByRole('alert').getByText('ACK incierto de capacidades tras GOV').waitFor();
  assert.deepEqual(await page.evaluate(()=>window.__calls.filter(c=>c.method==='PUT')[1].b),quotaRequest,
    'Uncertain retry must preserve the complete UUID/revision/quota payload');
  assert.equal(await page.evaluate(()=>Object.keys(window.__capacityOperations).length),1);
  // A real remount drops React state. Only the synthetic backend survives the reload.
  const serverState=await page.evaluate(()=>({__reads:window.__reads,__calls:window.__calls,
    __companies:window.__companies,__capabilities:window.__capabilities,
    __capacityOperations:window.__capacityOperations,__govValid:window.__govValid,
    __quotaHold:true,__quotaAckLossOnce:false,__quotaConflictOnce:false,__deny:false,__disabled:false,__failOnce:false}));
  const companyId=Object.values(serverState.__companies)[0].tenant_id;
  await page.reload();
  await page.evaluate(state=>Object.assign(window,state),serverState);
  await page.addScriptTag({content:js});
  await page.getByLabel('Identificador corporativo').fill(companyId);
  await click('Consultar estado de empresa');
  await page.getByText('Conciliación de capacidades pendiente. Reintenta con la misma referencia y cuotas; la habilitación sigue bloqueada.',{exact:true}).waitFor();
  await assertPending();
  assert.equal(await page.getByLabel('Máximo de sedes').inputValue(),'2');
  assert.equal(await page.getByLabel('Destinos máximos por sede').inputValue(),'10');
  assert.match(await page.getByText('Referencia de capacidades pendiente:').textContent(),new RegExp(quotaRequest.request_id));
  assert.equal(await page.evaluate(()=>window.__calls.length),serverState.__calls.length,'Recovery is read-only');
  await page.evaluate(()=>window.__quotaHold=false);
  await click('Reintentar conciliación');
  await page.getByText('Habilitación del directorio',{exact:true}).waitFor();
  assert.deepEqual(await page.evaluate(()=>window.__calls.filter(c=>c.method==='PUT')[2].b),quotaRequest,
    'Recovered pending operation must preserve UUID, expected revision and payload');
  assert.equal(await page.evaluate(()=>Object.keys(window.__capacityOperations).length),1);
  assert.equal(await page.getByRole('button',{name:'Habilitar directorio'}).isDisabled(),true);
  assert.equal(await page.evaluate(()=>window.__calls.filter(c=>c.p.endsWith('/habilitar-directorio')).length),0);
  await page.getByRole('checkbox').check();
  await click('Habilitar directorio');
  await page.getByRole('button',{name:'Directorio habilitado'}).waitFor();
  assert.equal(await page.evaluate(()=>window.__calls.filter(c=>c.p.endsWith('/habilitar-directorio')).length),1);
  assert.equal(await page.evaluate(()=>Object.values(window.__companies)[0].directorio_habilitado),true);
  for(const width of [320,360,1280]){
    await page.setViewportSize({width,height:800});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,
      'Horizontal overflow at '+width);
  }
  const mutationCount=await page.evaluate(()=>window.__calls.length);
  await click('Comenzar otra alta');
  await page.getByRole('button',{name:'Crear empresa deshabilitada'}).waitFor();
  await page.getByLabel('Identificador corporativo').fill(companyId);
  await click('Consultar estado de empresa');
  await page.getByRole('button',{name:'Directorio habilitado'}).waitFor();
  assert.equal(await page.evaluate(()=>window.__calls.length),mutationCount,'No mutation during recovery');
  await click('Comenzar otra alta');
  assert.equal(await page.getByLabel('Nombre de empresa').inputValue(),'');
  assert.equal(await page.evaluate(()=>Object.keys(window.__companies).length),1);
  // Legacy quotas without a durable operation are never authority to activate.
  const legacyId='corp_'+'b'.repeat(32);
  await page.evaluate(id=>{
    const existing=Object.values(window.__companies)[0];
    window.__companies.legacy={...structuredClone(existing),tenant_id:id,nombre:'Legacy sintética',
      directorio_habilitado:false,capacidades_operacion:null,capacidades_revision:0};
    window.__capabilities={max_sedes:3,max_destinos_por_sede:12};
  },legacyId);
  await page.getByLabel('Identificador corporativo').fill(legacyId);
  await click('Consultar estado de empresa');
  await page.getByText('Las cuotas no están confirmadas en CORE y GOV. Guarda capacidades explícitamente antes de habilitar.',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Habilitar directorio',exact:true}).count(),0);
  assert.equal(await page.getByLabel('Máximo de sedes').isDisabled(),false);
  assert.equal(await page.getByLabel('Máximo de sedes').inputValue(),'3');
  // Losing the ACK after CORE confirms must still replay, not create another operation.
  await page.evaluate(()=>{window.__quotaConflictOnce=true;window.__quotaAckLossOnce=true;});
  await click('Guardar capacidades');
  await page.getByRole('alert').getByText('Conflicto de configuración').waitFor();
  const conflicted=await page.evaluate(()=>window.__calls.filter(c=>c.method==='PUT').at(-1).b);
  assert.equal(await page.getByLabel('Máximo de sedes').isDisabled(),true);
  assert.equal(await page.getByRole('button',{name:'Habilitar directorio',exact:true}).count(),0);
  await click('Reintentar conciliación');
  await page.getByRole('alert').getByText('ACK perdido de capacidades confirmadas').waitFor();
  const lostAck=await page.evaluate(()=>window.__calls.filter(c=>c.method==='PUT').at(-1).b);
  assert.deepEqual(lostAck,conflicted,'409 must not silently rotate UUID or alter payload/revision');
  assert.equal(lostAck.expected_revision,0);
  assert.equal(await page.getByLabel('Máximo de sedes').isDisabled(),true);
  assert.equal(await page.getByRole('button',{name:'Habilitar directorio',exact:true}).count(),0);
  await click('Reintentar conciliación');
  await page.getByText('Habilitación del directorio',{exact:true}).waitFor();
  assert.deepEqual(await page.evaluate(()=>window.__calls.filter(c=>c.method==='PUT').at(-1).b),lostAck);
  assert.equal(await page.evaluate(()=>Object.keys(window.__capacityOperations).length),2);
  // A confirmed CORE marker alone is insufficient after GOV validity is lost.
  await click('Comenzar otra alta');
  await page.evaluate(()=>window.__govValid=false);
  await page.getByLabel('Identificador corporativo').fill(legacyId);
  await click('Consultar estado de empresa');
  await page.getByRole('button',{name:'Guardar capacidades',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Habilitar directorio',exact:true}).count(),0);
  await click('Guardar capacidades');
  await page.getByText('Habilitación del directorio',{exact:true}).waitFor();
  const renewed=await page.evaluate(()=>window.__calls.filter(c=>c.method==='PUT').at(-1).b);
  assert.notEqual(renewed.request_id,lostAck.request_id);
  assert.equal(renewed.expected_revision,1,'New intent uses the last durable revision');
  assert.equal(await page.evaluate(()=>window.__calls.filter(c=>c.p.endsWith('/habilitar-directorio')).length),1,
    'No automatic activation during any quota reconciliation');
  await click('Comenzar otra alta');
  await page.evaluate(()=>{window.__companies.legacy.capacidades_operacion.estado='needs_review';window.__govValid=false;});
  const beforeReview=await page.evaluate(()=>window.__calls.length);
  await page.getByLabel('Identificador corporativo').fill(legacyId);
  await click('Consultar estado de empresa');
  await page.getByRole('button',{name:'Revisión requerida',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Revisión requerida',exact:true}).isDisabled(),true);
  assert.equal(await page.getByLabel('Máximo de sedes').isDisabled(),true);
  assert.equal(await page.getByLabel('Destinos máximos por sede').isDisabled(),true);
  assert.equal(await page.getByRole('button',{name:'Habilitar directorio',exact:true}).count(),0);
  assert.equal(await page.getByRole('button',{name:'Guardar capacidades',exact:true}).count(),0);
  assert.equal(await page.getByRole('button',{name:'Reintentar conciliación',exact:true}).count(),0);
  assert.match(await page.getByText('Referencia de capacidades en revisión:').textContent(),new RegExp(renewed.request_id));
  assert.equal(await page.evaluate(()=>window.__calls.length),beforeReview,'needs_review must never create or replay operations');
  console.log('PASS: synthetic GLOBAL denial, owner verification, creation replay, quota UUID/revision replay, blocked edits, pending reload recovery, legacy/GOV validity fail-closed, 409 stable UUID, lost confirmation ACK, needs_review block, explicit activation, mobile widths; no real network.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

