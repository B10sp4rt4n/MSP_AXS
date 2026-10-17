const {test}=require('node:test'), assert=require('node:assert/strict'), ts=require('typescript'), fs=require('fs'), vm=require('vm');
function load(file){const mod={exports:{}};const js=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;vm.runInThisContext(`(function(exports,require){${js}\n})`)(mod.exports,()=>load('src/lib/presencia.ts'));return mod.exports;}
const {buscarVisitas,evaluarVisita}=load('src/lib/guardia-flow.ts');
const now=Date.parse('2026-10-17T15:00:00Z');
const reglas={exigir_autorizacion:true,exigir_proposito:true,tipos_visita:['eventual']};
const base={visita_id:'v1',nombre_visitante:'María Pérez',casa_unidad:'24',condominio_id:'a',tipo_visita:'eventual',estado:'pendiente',proposito:'Entrega',autorizada_por:'r',autorizada_en:'2026-10-17T14:00:00Z',vigencia:'2026-10-17T15:00:00Z',entrada_registrada_en:null,salida_registrada_en:null,qr_token:null};
test('salida recupera entrada de ayer aunque autorización y QR hayan vencido',()=>{const v={...base,estado:'entrada_registrada',vigencia:'2026-10-16T15:00:00Z',entrada_registrada_en:'2026-10-16T15:00:00Z',qr_token:'old',qr_vigencia:'2026-10-16T16:00:00Z'};assert.equal(evaluarVisita(v,'salida',null,null,now).permitida,true);assert.equal(buscarVisitas([v],'maria','salida').length,1);});
test('cerradas no son recuperables como abiertas; historial sí permite revisarlas',()=>{const v={...base,estado:'salida_registrada',entrada_registrada_en:'2026-10-17T13:00:00Z',salida_registrada_en:'2026-10-17T14:00:00Z'};assert.equal(buscarVisitas([v],'24','salida').length,0);assert.equal(buscarVisitas([v],'24','salida',true).length,1);assert.equal(evaluarVisita(v,'salida',reglas,null,now).permitida,false);});
test('autorización, tiempo y QR requeridos no se evaden por buscar sin QR',()=>{assert.equal(evaluarVisita(base,'entrada',reglas,null,now).permitida,true);for(const changes of [{autorizada_por:null},{proposito:''},{vigencia:'2026-10-16T15:00:00Z'},{vigencia:'2026-10-18T15:00:00Z'},{qr_token:'required'}])assert.equal(evaluarVisita({...base,...changes},'entrada',reglas,null,now).permitida,false);});
test('no mezcla homónimos: búsqueda devuelve ambas visitas y permite precisar vivienda o placa',()=>{const other={...base,visita_id:'v2',casa_unidad:'25',placa:'ABC123'};assert.equal(buscarVisitas([base,other],'maria','entrada').length,2);assert.equal(buscarVisitas([base,other],'maria 25','entrada')[0].visita_id,'v2');assert.equal(buscarVisitas([base,other],'abc123','entrada')[0].visita_id,'v2');});
test('fechas inconsistentes y estado cancelado bloquean acciones',()=>{for(const v of [{...base,estado:'cancelada'},{...base,estado:'entrada_registrada',entrada_registrada_en:'bad'},{...base,estado:'entrada_registrada',entrada_registrada_en:'2026-10-18T15:00:00Z'}]){assert.equal(evaluarVisita(v,'entrada',reglas,null,now).permitida,false);assert.equal(evaluarVisita(v,'salida',reglas,null,now).permitida,false);}});

test('permiso remoto requerido aun con reglas opcionales apagadas; QR sigue obligatorio',()=>{
 const r={exigir_autorizacion:false,exigir_proposito:false,tipos_visita:[]};
 const v={...base,solicitud_remota_id:'request',autorizacion_remota_hasta:'2026-10-17T15:05:00Z'};
 assert.equal(evaluarVisita(v,'entrada',r,null,now).permitida,true);
 for(const change of [{autorizacion_remota_hasta:null},{autorizacion_remota_hasta:'2026-10-17T15:00:00Z'},{autorizada_por:null},{qr_token:'obligatorio'}])
  assert.equal(evaluarVisita({...v,...change},'entrada',r,null,now).permitida,false);
});
