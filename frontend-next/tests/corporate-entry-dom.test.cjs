// Synthetic DOM regression. Clerk, routing, storage and API are isolated;
// this does not certify independent Clerk sessions in the deployed sandbox.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ts=require('typescript');
const {JSDOM}=require('jsdom');
const dom=new JSDOM('<!doctype html><body></body>',{url:'https://fixture.invalid'});
global.window=dom.window;global.document=dom.window.document;
global.HTMLElement=dom.window.HTMLElement;global.IS_REACT_ACT_ENVIRONMENT=true;
global.fetch=async()=>{throw Error('Real network forbidden');};
const React=require('react'),{act}=React,{createRoot}=require('react-dom/client');
const tenant='corp_fixture',site='site_fixture';
const directory='/dashboard/corporativo?empresa='+tenant;
const visits=directory.replace('corporativo?','corporativo/visitas?')+'&sede='+site;

async function fixture(t,options={}){
 window.localStorage.clear();
 const state={userId:'account-a',role:'RESIDENTE',corporateRole:'owner',token:'test',calls:[],routes:[],...options};
 const getToken=async()=>state.token;
 const router={replace:href=>state.routes.push(href)};
 const api={get:async(route,token,signal)=>{
  state.calls.push({route,token,signal});
  if(route==='/auth/me')return{rol:state.role,nombre:'Fixture',condominio_id:null};
  if(state.hold)await state.hold;
  if(state.denied)throw Error('Denied');
  if(route.endsWith('/capacidades'))return{role:state.corporateRole};
  if(route.endsWith('/sedes'))return[];
  throw Error('Unexpected route '+route);
 }};
 const cache=new Map();
 function load(relative){
  if(cache.has(relative))return cache.get(relative);
  const filename=path.resolve(__dirname,'../src',relative),module={exports:{}};
  const source=ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{
   module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,
  }}).outputText;
  const requireMock=name=>name==='@clerk/nextjs'?{
   useAuth:()=>({isLoaded:true,userId:state.userId,getToken}),
   useUser:()=>({user:null}),UserButton:()=>null,
  }:name==='next/navigation'?{useRouter:()=>router}:name==='@/lib/api'?{api}
   :name==='@/components/AxsBrand'?{__esModule:true,default:()=>null}
   :name.startsWith('@/')?load(name.slice(2)+'.ts'):require(name);
  vm.runInThisContext(`(function(require,module,exports){${source}\n})`,{filename})(requireMock,module,module.exports);
  cache.set(relative,module.exports);return module.exports;
 }
 const entry=load('lib/corporate-entry.ts');
 const Dashboard=load('app/dashboard/DashboardClient.tsx').default;
 const container=document.createElement('div');document.body.append(container);
 const root=createRoot(container);
 const mount=()=>act(async()=>{root.render(React.createElement(Dashboard));});
 t.after(async()=>{await act(async()=>root.unmount());container.remove();});
 return{state,entry,container,mount};
}

for(const role of ['owner','admin','host','reception'])test('server-verified '+role+' opens the correct corporate page',async t=>{
 const f=await fixture(t,{corporateRole:role});
 f.entry.rememberCorporateWorkspace('account-a',{tenant,site});await f.mount();
 assert.deepEqual(f.state.routes,[['owner','admin'].includes(role)?directory:visits]);
 assert.equal(f.container.textContent.includes('casa asignada'),false);
 assert.equal(f.state.calls.some(c=>c.route.includes('/plataforma/')),false);
 assert.equal(f.state.calls.at(-1).route,`/corporativo/${tenant}/sedes/${site}/visitas/capacidades`);
});

test('a directory-only bookmark verifies membership before navigation',async t=>{
 const f=await fixture(t);f.entry.rememberCorporateWorkspace('account-a',{tenant});await f.mount();
 assert.deepEqual(f.state.routes,[directory]);assert.equal(f.state.calls.at(-1).route,`/corporativo/${tenant}/sedes`);
});

test('residential account without a bookmark keeps its portal and gets an explicit corporate entry',async t=>{
 const f=await fixture(t);await f.mount();
 assert.equal(f.container.querySelector('a[href="/dashboard/residente"]')!==null,true);
 assert.equal(f.container.querySelector('a[href="/dashboard/corporativo"]')!==null,true);
 assert.deepEqual(f.state.routes,[]);assert.equal(f.state.calls.length,1);
});

test('one Clerk account never inherits another account bookmark',async t=>{
 const f=await fixture(t,{userId:'account-b'});
 f.entry.rememberCorporateWorkspace('account-a',{tenant,site});await f.mount();
 assert.deepEqual(f.state.routes,[]);assert.equal(f.state.calls.length,1);
 assert.equal(f.entry.readCorporateWorkspace('account-b'),null);
});

test('a denied bookmark does not reveal residential controls; choosing another entry clears only this account',async t=>{
 const f=await fixture(t,{denied:true});
 f.entry.rememberCorporateWorkspace('account-a',{tenant,site});
 f.entry.rememberCorporateWorkspace('account-b',{tenant:'corp_other',site});await f.mount();
 assert.deepEqual(f.state.routes,[]);assert.equal(f.container.querySelector('a[href="/dashboard/residente"]'),null);
 assert.match(f.container.textContent,/No pudimos comprobar tus permisos/);
 const button=[...f.container.querySelectorAll('button')].find(b=>b.textContent==='Usar otro acceso');
 await act(async()=>button.click());
 assert.equal(f.entry.readCorporateWorkspace('account-a'),null);
 assert.deepEqual(f.entry.readCorporateWorkspace('account-b'),{tenant:'corp_other',site});
 assert.ok(f.container.querySelector('a[href="/dashboard/residente"]'));
});

test('unknown corporate role fails closed',async t=>{
 const f=await fixture(t,{corporateRole:'GLOBAL'});f.entry.rememberCorporateWorkspace('account-a',{tenant,site});await f.mount();
 assert.deepEqual(f.state.routes,[]);assert.match(f.container.textContent,/No pudimos comprobar/);
});

test('corrupt or executable paths in storage are ignored',async t=>{
 const f=await fixture(t);
 window.localStorage.setItem('axs:corporate-workspace:v1:account-a',JSON.stringify({tenant:'javascript:alert(1)',site}));
 await f.mount();assert.deepEqual(f.state.routes,[]);assert.equal(f.state.calls.length,1);
 f.entry.rememberCorporateWorkspace('account-b',{tenant,site:'//other.invalid'});
 assert.equal(f.entry.readCorporateWorkspace('account-b'),null);
 f.entry.rememberCorporateWorkspace('account-b',{tenant,site,role:'owner',token:'never-persist'});
 assert.deepEqual(JSON.parse(window.localStorage.getItem('axs:corporate-workspace:v1:account-b')),{tenant,site});
});

test('switching identity during verification cancels the old navigation',async t=>{
 let release;const hold=new Promise(r=>release=r);
 const f=await fixture(t,{hold});f.entry.rememberCorporateWorkspace('account-a',{tenant,site});await f.mount();
 f.state.userId='account-b';f.state.hold=null;await f.mount();
 await act(async()=>release());
 assert.deepEqual(f.state.routes,[]);assert.equal(f.state.calls[1].signal.aborted,true);
});

test('missing token and signed-out sessions perform no corporate requests',async t=>{
 const f=await fixture(t,{token:null});f.entry.rememberCorporateWorkspace('account-a',{tenant,site});await f.mount();
 assert.deepEqual(f.state.calls,[]);assert.deepEqual(f.state.routes,[]);
 f.state.userId=null;await f.mount();assert.deepEqual(f.state.calls,[]);
});
