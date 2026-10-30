// Local DOM regression, not browser QA. No real Clerk/backend or network access.
// Setup without changing manifests: npm install --no-save --package-lock=false jsdom@26.1.0
// Run: node --test tests/corporate-reconciliation-dom.test.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ts=require('typescript');
const {JSDOM,ResourceLoader}=require('jsdom');

class NoNetwork extends ResourceLoader {
  fetch(url){throw Error('External resource forbidden in DOM test: '+url);}
}
const dom=new JSDOM('<!doctype html><html><body></body></html>',{
  url:'http://localhost/',resources:new NoNetwork(),pretendToBeVisual:true,
});
global.window=dom.window;
global.document=dom.window.document;
global.HTMLElement=dom.window.HTMLElement;
global.IS_REACT_ACT_ENVIRONMENT=true;
global.fetch=async()=>{throw Error('Real network forbidden in corporate DOM test');};
const React=require('react');
const {act}=React;
const {createRoot}=require('react-dom/client');

const tenant='corp_'+'a'.repeat(32);
const uuid='12345678-1234-4234-8234-123456789abc';
const filename=path.resolve(__dirname,'../src/app/dashboard/corporativo-superadmin/CorporativoSuperadminClient.tsx');
const source=ts.transpileModule(fs.readFileSync(filename,'utf8'),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022},
}).outputText;

class ApiError extends Error {
  constructor(message,status){super(message);this.status=status;}
}

async function fixture(t,{operation=null,quotas=null,govValid=true,mode='confirm'}={}){
  const state={operation:structuredClone(operation),quotas:structuredClone(quotas),govValid,mode,
    calls:[],reads:[],operations:new Map(),enabled:false};
  if(state.operation)state.operations.set(state.operation.request_id,state.operation);
  const confirmed=()=>!!(state.govValid&&state.operation?.estado==='confirmed'&&
    state.quotas?.request_id===state.operation.request_id&&
    state.quotas.max_sedes===state.operation.max_sedes&&
    state.quotas.max_destinos_por_sede===state.operation.max_destinos_por_sede);
  const company=()=>({tenant_id:tenant,nombre:'Empresa sintética',msp_id:'msp_fixture',
    owner_user_id:'owner_fixture',modalidad:'corporativo',directorio_habilitado:state.enabled,
    privacy_contact:'privacy@example.test',privacy_notice_version:'fixture-1',
    capacidades:state.quotas?{max_sedes:state.quotas.max_sedes,max_destinos_por_sede:state.quotas.max_destinos_por_sede}
      :{max_sedes:null,max_destinos_por_sede:null},
    capacidades_operacion:structuredClone(state.operation),capacidades_revision:state.operation?.revision??0,
    capacidades_confirmadas:confirmed()});
  const api={
    get:async route=>{
      state.reads.push(route);
      if(route==='/plataforma/corporativo/acceso')return{authorized:true,provisioning_enabled:true,credencial_configurada:true};
      if(route==='/plataforma/corporativo/empresas/'+tenant)return company();
      throw Error('Unexpected GET '+route);
    },
    put:async(route,body)=>{
      state.calls.push({method:'PUT',route,body:structuredClone(body)});
      assert.equal(route,'/plataforma/corporativo/empresas/'+tenant+'/capacidades');
      assert.match(body.request_id,/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
      assert.equal(Number.isInteger(body.expected_revision),true);
      if(state.mode==='conflict')throw new ApiError('Conflicto de configuración',409);
      if(state.operation?.estado==='needs_review')throw new ApiError('Revisión requerida',409);
      let operation=state.operations.get(body.request_id);
      if(operation){
        for(const key of ['expected_revision','max_sedes','max_destinos_por_sede'])
          if(operation[key]!==body[key])throw new ApiError('Referencia reutilizada',409);
      }else{
        if(state.operation?.estado==='pending')throw new ApiError('Operación pendiente',409);
        if(body.expected_revision!==(state.operation?.revision??0))throw new ApiError('Revisión obsoleta',409);
        operation={...body,revision:body.expected_revision+1,estado:'pending'};
        state.operations.set(body.request_id,operation);
      }
      state.operation=operation;
      state.quotas={request_id:body.request_id,max_sedes:body.max_sedes,max_destinos_por_sede:body.max_destinos_por_sede};
      state.govValid=true;
      if(state.mode==='hold')throw Error('ACK incierto después de GOV');
      operation.estado='confirmed';
      if(state.mode==='ack_lost'){state.mode='confirm';throw Error('ACK perdido después de CORE');}
      if(state.mode==='invalid_gov')state.govValid=false;
      return{tenant_id:tenant,request_id:body.request_id,estado:'confirmed',revision:operation.revision,
        cuotas:{max_sedes:body.max_sedes,max_destinos_por_sede:body.max_destinos_por_sede}};
    },
    post:async(route,body)=>{
      state.calls.push({method:'POST',route,body:structuredClone(body)});
      assert.equal(route,'/plataforma/corporativo/empresas/'+tenant+'/habilitar-directorio');
      assert.equal(body.confirmacion,true);
      assert.equal(confirmed(),true);
      state.enabled=true;
      return company();
    },
  };
  const token=async()=>'synthetic-token';
  const module={exports:{}};
  const requireMock=name=>name==='@clerk/nextjs'?{useAuth:()=>({getToken:token,isLoaded:true,userId:'global_fixture'})}
    :name==='@/lib/api'?{api,ApiError}:require(name);
  vm.runInThisContext(`(function(require,module,exports){${source}\n})`,{filename})(requireMock,module,module.exports);
  const container=document.createElement('div');document.body.append(container);
  let root=createRoot(container);
  const mount=async()=>{await act(async()=>{root.render(React.createElement(module.exports.default));});};
  t.after(async()=>{await act(async()=>root.unmount());container.remove();});
  await mount();
  const button=text=>Array.from(container.querySelectorAll('button')).find(el=>el.textContent===text);
  const input=id=>container.querySelector('#'+id);
  const change=async(id,value)=>{
    const el=input(id);assert.ok(el,'Missing input '+id);assert.equal(el.disabled,false,'Cannot edit disabled input '+id);
    await act(async()=>{
      Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype,'value').set.call(el,String(value));
      el.dispatchEvent(new dom.window.Event('input',{bubbles:true}));
    });
  };
  const click=async text=>{
    const el=button(text);assert.ok(el,'Missing button '+text);
    await act(async()=>el.click());
  };
  const load=async()=>{await change('corporate-lookup',tenant);await click('Consultar estado de empresa');};
  const noActivation=()=>{
    assert.equal(button('Habilitar directorio'),undefined);
    assert.equal(container.querySelector('input[type="checkbox"]'),null);
    assert.equal(state.calls.filter(c=>c.method==='POST').length,0);
  };
  const pending=()=>{
    assert.equal(input('max_sedes').disabled,true);
    assert.equal(input('max_destinos_por_sede').disabled,true);
    assert.ok(button('Reintentar conciliación'));
    assert.equal(button('Comenzar otra alta').disabled,true);
    noActivation();
  };
  const remount=async()=>{
    await act(async()=>root.unmount());
    root=createRoot(container);
    await mount();
  };
  return{state,container,button,input,change,click,load,noActivation,pending,remount};
}

test('ACK incierto congela UUID, revisión y cuotas; sólo confirma después de conciliar',async t=>{
  const app=await fixture(t,{mode:'hold'});
  await app.load();
  await app.change('max_sedes',3);await app.change('max_destinos_por_sede',12);
  await app.click('Guardar capacidades');
  app.pending();
  assert.match(app.container.textContent,/ACK incierto después de GOV/);
  const original=app.state.calls[0].body;
  assert.equal(original.expected_revision,0);
  assert.equal(original.max_sedes,3);assert.equal(original.max_destinos_por_sede,12);
  await assert.rejects(app.change('max_sedes',999),/Cannot edit disabled input/);
  await app.click('Comenzar otra alta');
  app.pending();
  await app.click('Reintentar conciliación');
  assert.deepEqual(app.state.calls[1].body,original);
  assert.equal(app.state.operations.size,1);
  app.pending();
  app.state.mode='confirm';
  await app.click('Reintentar conciliación');
  assert.deepEqual(app.state.calls[2].body,original);
  assert.equal(app.state.operation.estado,'confirmed');
  assert.equal(app.button('Habilitar directorio').disabled,true,'Explicit activation confirmation still required');
  assert.equal(app.state.calls.filter(c=>c.method==='POST').length,0);
  await act(async()=>app.container.querySelector('input[type="checkbox"]').click());
  assert.equal(app.button('Habilitar directorio').disabled,false);
  await app.click('Habilitar directorio');
  assert.equal(app.state.enabled,true);
});

test('recarga real del componente recupera pending y expected_revision del marcador, no la revisión actual',async t=>{
  const operation={request_id:uuid,expected_revision:7,revision:8,estado:'pending',max_sedes:5,max_destinos_por_sede:23};
  const app=await fixture(t,{operation,quotas:{request_id:uuid,max_sedes:5,max_destinos_por_sede:23}});
  await app.load();
  await app.remount();
  await app.load();
  app.pending();
  assert.match(app.container.textContent,/Conciliación de capacidades pendiente/);
  assert.match(app.container.textContent,new RegExp(uuid));
  assert.equal(app.input('max_sedes').value,'5');assert.equal(app.input('max_destinos_por_sede').value,'23');
  assert.equal(app.state.calls.length,0,'Reading/recovery must not mutate');
  await app.click('Reintentar conciliación');
  assert.deepEqual(app.state.calls[0].body,{request_id:uuid,expected_revision:7,max_sedes:5,max_destinos_por_sede:23});
  assert.equal(app.state.operations.size,1);
  assert.ok(app.button('Habilitar directorio'));
  assert.equal(app.state.calls.filter(c=>c.method==='POST').length,0);
});

test('needs_review conserva referencia y bloquea escrituras y habilitación',async t=>{
  const operation={request_id:uuid,expected_revision:2,revision:3,estado:'needs_review',max_sedes:7,max_destinos_por_sede:19};
  const app=await fixture(t,{operation,quotas:{request_id:uuid,max_sedes:7,max_destinos_por_sede:19}});
  await app.load();
  assert.match(app.container.textContent,/requiere revisión por cambios en GOV/);
  assert.match(app.container.textContent,new RegExp(uuid));
  assert.equal(app.input('max_sedes').disabled,true);assert.equal(app.input('max_destinos_por_sede').disabled,true);
  assert.equal(app.button('Revisión requerida').disabled,true);
  assert.equal(app.button('Guardar capacidades'),undefined);assert.equal(app.button('Reintentar conciliación'),undefined);
  await app.click('Revisión requerida');
  app.noActivation();
  assert.equal(app.state.calls.length,0);assert.equal(app.state.operations.size,1);
});

test('cuotas legacy iguales no autorizan habilitación sin operación durable',async t=>{
  const app=await fixture(t,{quotas:{max_sedes:3,max_destinos_por_sede:12}});
  await app.load();
  app.noActivation();
  assert.equal(app.input('max_sedes').disabled,false);
  assert.match(app.container.textContent,/Guarda capacidades explícitamente/);
  await app.click('Guardar capacidades');
  assert.equal(app.state.calls[0].body.expected_revision,0);
  assert.equal(app.state.operations.size,1);
  assert.ok(app.button('Habilitar directorio'));
});

test('409 y pérdida de ACK tras confirmación no cambian UUID ni crean otra operación',async t=>{
  const app=await fixture(t,{mode:'conflict'});
  await app.load();await app.click('Guardar capacidades');
  app.pending();
  assert.match(app.container.textContent,/Conflicto de configuración/);
  const original=app.state.calls[0].body;
  app.state.mode='ack_lost';
  await app.click('Reintentar conciliación');
  app.pending();
  assert.equal(app.state.operation.estado,'confirmed');
  assert.match(app.container.textContent,/ACK perdido después de CORE/);
  await app.click('Reintentar conciliación');
  assert.deepEqual(app.state.calls.map(c=>c.body),[original,original,original]);
  assert.equal(app.state.operations.size,1);
  assert.ok(app.button('Habilitar directorio'));
});

test('respuesta PUT confirmed no basta si GET no confirma GOV, aunque los números coincidan',async t=>{
  const app=await fixture(t,{mode:'invalid_gov'});
  await app.load();await app.click('Guardar capacidades');
  app.pending();
  assert.equal(app.state.operation.estado,'confirmed');
  assert.equal(app.state.quotas.max_sedes,app.state.calls[0].body.max_sedes);
  assert.match(app.container.textContent,/no aparecen confirmadas en CORE y GOV/);
});
