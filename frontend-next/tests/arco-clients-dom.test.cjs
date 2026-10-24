// Real React component, synthetic API/Clerk, no external network or credentials.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ts=require('typescript');
const {JSDOM,ResourceLoader}=require('jsdom');
class NoNetwork extends ResourceLoader{fetch(url){throw Error('Forbidden network: '+url)}}
const dom=new JSDOM('<body></body>',{url:'http://localhost/',resources:new NoNetwork()});
Object.assign(global,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,
  FormData:dom.window.FormData,IS_REACT_ACT_ENVIRONMENT:true});
global.fetch=async()=>{throw Error('Real network forbidden')};
const React=require('react'),{act}=React,{createRoot}=require('react-dom/client');
const filename=path.resolve(__dirname,'../src/app/dashboard/arco/ArcoClient.tsx');
const source=ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
class ApiError extends Error{constructor(message,status){super(message);this.status=status}}
const clients=[{tenant_id:'res',nombre:'Residencial',modalidad:'residencial'},
  {tenant_id:'corp',nombre:'Empresa',modalidad:'corporativo'}];
const row={case_id:'00000000-0000-4000-8000-000000000001',subject_ref:'CORP_PRIVATE',owner_id:'operator',
  right:'acceso',received_at:'2026-01-01T12:00:00Z',determination_due:'2026-01-20T12:00:00Z',
  execution_due:null,state:'recibida',version:1,pending_actions:0,history:[]};

async function fixture(t){
  const state={clients:structuredClone(clients),userId:'privacy',sessionId:'session1',reads:[],writes:[],
    rows:{res:[],corp:[structuredClone(row)]},blocked:false,disabled:false,slow:null,resolve:null};
  const api={get:async p=>{
    state.reads.push(p);
    if(p==='/arco-clientes'){if(state.disabled)throw new ApiError('Disabled',404);return structuredClone(state.clients)}
    if(!p.startsWith('/arco/'))throw Error('Unexpected GET '+p);
    if(state.blocked)throw new ApiError('Sin permisos vigentes',403);
    const id=p.split('/')[2].split('?')[0];
    if(state.slow===id)return new Promise(resolve=>state.resolve=resolve);
    return structuredClone(state.rows[id]);
  },post:async(p,body)=>{state.writes.push({p,body});return{}}};
  const token=async()=>'synthetic';
  const module={exports:{}};
  const mocked=name=>name==='@clerk/nextjs'?{useAuth:()=>({getToken:token,userId:state.userId,sessionId:state.sessionId})}
    :name==='@/lib/api'?{api,ApiError}:name==='next/link'?{default:({children,...props})=>React.createElement('a',props,children)}:require(name);
  vm.runInThisContext(`(function(require,module,exports){${source}\n})`,{filename})(mocked,module,module.exports);
  const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
  const render=()=>act(async()=>root.render(React.createElement(module.exports.default)));
  await render();
  t.after(async()=>{await act(async()=>root.unmount());container.remove()});
  const select=async id=>{await act(async()=>{
    const el=container.querySelector('select[aria-label="Cliente"]');el.value=id;
    el.dispatchEvent(new dom.window.Event('change',{bubbles:true}));
  })};
  const click=async text=>{const el=[...container.querySelectorAll('button')].find(e=>e.textContent===text);
    assert.ok(el,'Missing button '+text);await act(async()=>el.click())};
  return{state,container,render,select,click};
}

test('selector uses private ARCO clients and labels both business modes',async t=>{
  const f=await fixture(t);
  assert.deepEqual(f.state.reads,['/arco-clientes']);
  assert.match(f.container.textContent,/Empresa · Empresa/);
  assert.match(f.container.textContent,/Residencial · Condominio/);
  await f.select('corp');assert.match(f.container.textContent,/CORP_PRIVATE/);
  await f.select('res');assert.doesNotMatch(f.container.textContent,/CORP_PRIVATE/);
  assert.match(f.container.textContent,/No hay expedientes/);
});

test('late response from previous client cannot populate the current client',async t=>{
  const f=await fixture(t);f.state.slow='res';
  await f.select('res');assert.equal(typeof f.state.resolve,'function');
  await f.select('corp');assert.match(f.container.textContent,/CORP_PRIVATE/);
  await act(async()=>f.state.resolve([{...row,subject_ref:'STALE_RESIDENTIAL'}]));
  assert.match(f.container.textContent,/CORP_PRIVATE/);
  assert.doesNotMatch(f.container.textContent,/STALE_RESIDENTIAL/);
});

test('switching Clerk user/session immediately discards private case state',async t=>{
  const f=await fixture(t);await f.select('corp');assert.match(f.container.textContent,/CORP_PRIVATE/);
  f.state.clients=[];f.state.userId='other';f.state.sessionId='session2';await f.render();
  assert.doesNotMatch(f.container.textContent,/CORP_PRIVATE/);
  assert.match(f.container.textContent,/No tienes clientes/);
  assert.equal(f.container.querySelectorAll('form').length,0);
});

test('authorization revocation and disabled ARCO never expose forms',async t=>{
  const f=await fixture(t);f.state.blocked=true;await f.select('corp');
  assert.match(f.container.textContent,/Sin permisos vigentes/);
  assert.equal(f.container.querySelectorAll('form').length,0);
  f.state.disabled=true;await f.click('Actualizar clientes');
  assert.match(f.container.textContent,/El registro ARCO no está habilitado/);
  assert.equal(f.container.querySelectorAll('form').length,0);
  assert.deepEqual(f.state.writes,[]);
});
