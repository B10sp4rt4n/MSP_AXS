const {test}=require('node:test'),assert=require('node:assert/strict'),ts=require('typescript'),fs=require('fs'),vm=require('vm');
const mod={exports:{}};const source=ts.transpileModule(fs.readFileSync('src/lib/guardia-destino.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;vm.runInThisContext(`(function(exports){${source}\n})`)(mod.exports);
const {buscarDestinos,visitaEnDestino}=mod.exports;
const a={casa_id:'a',numero:'24',tipo:'casa',residentes:[{nombre:'Laura Gómez'},{nombre:'Andrés Ruiz'}]};
const b={casa_id:'b',numero:'25',tipo:'casa',residentes:[{nombre:'Laura Díaz'}]};
test('buscar por cualquier residente, casa y destino sin interpretar tiempos',()=>{assert.deepEqual(buscarDestinos([a,b],'Laura').map(x=>x.casa_id),['a','b']);assert.equal(buscarDestinos([a,b],'andres')[0].casa_id,'a');assert.equal(buscarDestinos([a,b],'casa 24')[0].casa_id,'a');assert.equal(buscarDestinos([a,b],'').length,0);});
test('ID de destino prevalece sobre etiqueta; compatibilidad solo para visitas legacy',()=>{assert.equal(visitaEnDestino({destino_id:'b',casa_unidad:'24'},a),false);assert.equal(visitaEnDestino({destino_id:'a',casa_unidad:'old'},a),true);assert.equal(visitaEnDestino({casa_unidad:'24'},a),true);assert.equal(visitaEnDestino({casa_unidad:'25'},a),false);});
