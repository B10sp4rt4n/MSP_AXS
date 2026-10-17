const { test } = require('node:test');
const assert = require('node:assert/strict');
const ts = require('typescript');
const fs = require('node:fs');
const vm = require('node:vm');
const mod = { exports: {} };
const source = ts.transpileModule(fs.readFileSync('src/lib/presencia.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
vm.runInThisContext(`(function(exports){${source}\n})`)(mod.exports);
const { resumirPresencia, instante } = mod.exports;
const now = Date.parse('2026-10-17T13:00:00Z');
const visita = (id, estado, entrada, salida = null) => ({ visita_id: id, nombre_visitante: id, estado, entrada_registrada_en: entrada, salida_registrada_en: salida });
test('entradas antiguas sin salida; preregistros y cerradas no cuentan dentro', () => {
 const r = resumirPresencia([visita('antigua','entrada_registrada','2026-10-14T15:00:00Z'), visita('pendiente','pendiente',null), visita('activa','activa',null), visita('cerrada','salida_registrada','2026-10-15T15:00:00Z','2026-10-17T12:00:00Z')],now);
 assert.deepEqual(r.dentro.map(v=>v.visita_id),['antigua']);
 assert.equal(r.salidasHoy,1); assert.equal(r.entradasHoy,0);
 assert.equal(r.ultimo.visita.visita_id,'cerrada'); assert.equal(r.ultimo.tipo,'Salida');
});
test('medianoche de CDMX y UTC legacy sin zona', () => {
 const r=resumirPresencia([visita('ayer','entrada_registrada','2026-10-17T05:59:59Z'),visita('hoy','entrada_registrada','2026-10-17T06:00:00')],now);
 assert.equal(r.entradasHoy,1); assert.equal(r.dentro.length,2);
 assert.equal(instante('2026-10-17T06:00:00'), instante('2026-10-17T00:00:00-06:00'));
});
test('inconsistencias y fechas futuras no inventan presencia', () => {
 const rows=[visita('sinfecha','entrada_registrada',null),visita('cancelada','cancelada','2026-10-16T12:00:00Z'),visita('salidaantes','salida_registrada','2026-10-17T12:00:00Z','2026-10-16T12:00:00Z'),visita('invalida','entrada_registrada','no-fecha'),visita('futura','entrada_registrada','2026-10-18T12:00:00Z'),visita('sinentrada','salida_registrada',null,'2026-10-17T12:00:00Z')];
 const r=resumirPresencia(rows,now); assert.equal(r.revisar.length,rows.length); assert.equal(r.dentro.length,0); assert.equal(r.salidasHoy,0); assert.equal(r.ultimo,null);
});
test('ordena por antigüedad sin mutar la lista; último movimiento por fecha', () => {
 const rows=[visita('nueva','entrada_registrada','2026-10-17T12:30:00Z'),visita('vieja','entrada_registrada','2026-10-15T12:00:00Z')];
 const r=resumirPresencia(rows,now); assert.deepEqual(r.dentro.map(v=>v.visita_id),['vieja','nueva']); assert.equal(r.ultimo.visita.visita_id,'nueva'); assert.equal(rows[0].visita_id,'nueva');
});

test('detalle de tarjetas coincide con contadores y permite entrada y salida el mismo día', () => {
 const r=resumirPresencia([
  visita('ambas','salida_registrada','2026-10-17T07:00:00Z','2026-10-17T12:00:00Z'),
  visita('ayer','salida_registrada','2026-10-16T07:00:00Z','2026-10-17T08:00:00Z'),
  visita('dentro','entrada_registrada','2026-10-17T09:00:00Z'),
  visita('invalida','salida_registrada',null,'2026-10-17T10:00:00Z')
 ],now);
 assert.deepEqual(r.entradas.map(v=>v.visita_id),['ambas','dentro']);
 assert.deepEqual(r.salidas.map(v=>v.visita_id),['ambas','ayer']);
 assert.equal(r.entradas.length,r.entradasHoy);
 assert.equal(r.salidas.length,r.salidasHoy);
 assert.deepEqual(r.dentro.map(v=>v.visita_id),['dentro']);
});
