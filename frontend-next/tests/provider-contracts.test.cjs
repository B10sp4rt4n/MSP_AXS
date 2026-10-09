const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const vm = require('node:vm');
const mod = {exports:{}};
const js = ts.transpileModule(fs.readFileSync('src/lib/provider-contracts.ts','utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
vm.runInThisContext(`(function(exports){${js}\n})`)(mod.exports);
const { blockers, closeOperation, mexicoTime } = mod.exports;
const state = () => ({inventory:{condominio_id:'a/b',msp_id:'m',scopes:[
  {scope_id:1,estado:'revocado',origin:{kind:'msp',msp_id:'m',contract_id:'old'}},
  {scope_id:2,estado:'activo',origin:{kind:'condominio'}},
  {scope_id:3,estado:'activo',origin:{kind:'msp',msp_id:'m',contract_id:'second'}}]},
  contracts:[{contract_id:'old',closed_at:'2030-01-01'}, {contract_id:'second',version:2,closed_at:null}]});
test('la baja identifica contrato vigente y codifica condominio, conserva locales y revocados',()=>{
  const s=state(); assert.equal(blockers(s).length,0);
  const op=closeOperation(s,' fin ');
  assert.equal(op.path,'/condominios/a%2Fb/proveedor/baja');
  assert.deepEqual(op.body,{msp_id:'m',reason:'fin',contract_id:'second'});
});
test('scope reactivado del contrato antiguo o procedencia desconocida bloquean baja',()=>{
  const s=state();s.inventory.scopes[0].estado='activo';
  assert.deepEqual(blockers(s).map(x=>x.scope_id),[1]);
  assert.throws(()=>closeOperation(s,'fin'));
  s.inventory.scopes[0].origin={};assert.equal(blockers(s).length,1);
});
test('relación legacy no inventa contrato; sin proveedor o motivo no hay solicitud',()=>{
  const s=state();s.contracts=[];delete s.inventory.scopes[2].origin.contract_id;
  assert.equal(closeOperation(s,'fin').body.contract_id,undefined);
  assert.throws(()=>closeOperation(s,'  '));s.inventory.msp_id=null;
  assert.throws(()=>closeOperation(s,'fin'));
});
test('UTC sin zona produce la misma hora que UTC explícito',()=>{
  assert.equal(mexicoTime('2030-01-15T18:00:00'),mexicoTime('2030-01-15T18:00:00Z'));
  assert.match(mexicoTime('2030-01-15T18:00:00'),/12:00/);
});
