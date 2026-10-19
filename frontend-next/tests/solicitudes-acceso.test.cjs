const {test}=require('node:test'), assert=require('node:assert/strict'), fs=require('node:fs'),vm=require('node:vm'),ts=require('typescript'),React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
function render(rows,props={}) {
 let i=0;const states=[rows,'',false,true,false,'','','proveedor',null,null,Date.now()];
 const js=ts.transpileModule(fs.readFileSync('src/components/SolicitudesAcceso.tsx','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 const mod={exports:{}};
 vm.runInThisContext(`(function(require,module,exports){${js}\n})`)(name=>{
  if(name==='react')return {...React,useState:()=>[states[i++],()=>{}],useEffect:()=>{}};
  if(name==='@clerk/nextjs')return {useAuth:()=>({getToken:async()=>'test'})};
  if(name==='@/lib/api')return {api:{}};
  return require(name);
 },mod,mod.exports);
 return renderToStaticMarkup(React.createElement(mod.exports.default,{condominioId:'a',...props}));
}
const base={solicitud_id:'s',visita_id:'v',destino_id:'home',nombre_visitante:'Ana Pérez',casa_unidad:'101',proposito:'Entrega',estado:'pendiente',entrada_registrada:false,expira_en:new Date(Date.now()+300000).toISOString()};
test('guard hides consumed requests even with stale entry flag',()=>{
 const html=render([{...base,estado:'consumida'}]);assert.ok(!html.includes('Ana Pérez'));assert.ok(html.includes('No hay solicitudes para mostrar.'));
});
test('guard hides confirmed entries even with stale decision',()=>{
 for(const estado of ['pendiente','permitida','consumida'])assert.ok(!render([{...base,estado,entrada_registrada:true}]).includes('Ana Pérez'));
});
test('guard retains pending and permitted requests in the selected destination',()=>{
 for(const estado of ['pendiente','permitida']){assert.ok(render([{...base,estado}],{destinoId:'home'}).includes('Ana Pérez'));assert.ok(!render([{...base,estado}],{destinoId:'other'}).includes('Ana Pérez'));}
});
test('resident retains completed context without mutating stored request',()=>{
 const rows=[{...base,estado:'consumida',entrada_registrada:true}],before=JSON.stringify(rows),html=render(rows,{residente:true});
 assert.ok(html.includes('Ana Pérez'));assert.ok(html.includes('Entrada registrada en caseta.'));assert.equal(JSON.stringify(rows),before);
});
