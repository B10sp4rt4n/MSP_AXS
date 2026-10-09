const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
function render({ pagina = null, error = '', loading = false } = {}) {
  const states = [pagina, null, 0, error, loading];
  let index = 0;
  const source = ts.transpileModule(fs.readFileSync('src/components/Bitacora.tsx', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const mod = { exports: {} };
  vm.runInThisContext(`(function(require,module,exports){${source}\n})`)(name => {
    if (name === 'react') return { ...React, useState: () => [states[index++], () => {}], useEffect: () => {} };
    if (name === '@clerk/nextjs') return { useAuth: () => ({getToken: async () => 'test'}) };
    if (name === '@/lib/api') return { api: {} };
    return require(name);
  }, mod, mod.exports);
  return renderToStaticMarkup(React.createElement(mod.exports.default, {condominioId: 'a'}));
}
test('muestra actor, autorización, motivo, hora local y entrega pendiente', () => {
  const html = render({pagina: {items: [{id:1, visita_id:'visit-a', fecha:'2030-01-15T18:00:00Z', actor_id:'guard-a', accion:'registrar', resultado:'exito', motivo:'Salida registrada', estado:'salida_registrada', autorizada_por:'resident-a', proposito:'Servicio'}], siguiente:2, pendientes_entrega_condominio:3}});
  for (const text of ['guard-a','resident-a','Salida registrada','12:00','3 eventos','Anteriores']) assert.ok(html.includes(text), text);
});
test('error de consulta visible, sin anunciar lista vacía', () => {
  const html = render({error:'Servicio no disponible'});
  assert.ok(html.includes('role="alert"'));
  assert.ok(html.includes('Servicio no disponible'));
  assert.ok(!html.includes('Sin eventos recibidos'));
});
