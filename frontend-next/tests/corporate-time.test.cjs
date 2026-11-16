const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const vm = require('node:vm');
const mod = { exports: {} };
const source = ts.transpileModule(fs.readFileSync('src/lib/corporate-time.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
vm.runInThisContext(`(function(exports){${source}\n})`)(mod.exports);
const { corporateTime, validTimeZone } = mod.exports;
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

test('API UTC without suffix and explicit offsets identify the same instant', () => {
  for (const value of ['2026-11-16T11:49:59.009280', '2026-11-16T11:49:59.009280Z', '2026-11-16T05:49:59.009280-06:00']) {
    const time = corporateTime(value, 'America/Mexico_City');
    assert.equal(time.utc, '2026-11-16T11:49:59.009280Z');
    assert.ok(time.local.includes('05:49:59'), time.local);
    assert.equal(time.timeZone, 'America/Mexico_City');
  }
});
test('IANA zone rules handle seasonal changes and local date boundaries', () => {
  const winter = '2026-01-15T02:00:00Z', summer = '2026-07-15T02:00:00Z';
  assert.ok(corporateTime(winter, 'America/New_York').local.includes('21:00:00'));
  assert.ok(corporateTime(summer, 'America/New_York').local.includes('22:00:00'));
  for (const instant of [winter, summer]) {
    const cdmx = corporateTime(instant, 'America/Mexico_City');
    assert.ok(cdmx.local.includes('14/'), cdmx.local);
    assert.ok(cdmx.local.includes('20:00:00'), cdmx.local);
    assert.ok(corporateTime(instant, 'Asia/Tokyo').local.includes('11:00:00'));
    assert.equal(cdmx.utc, corporateTime(instant, 'Asia/Tokyo').utc);
  }
});
test('invalid or missing site zone falls back explicitly to UTC; invalid date is not guessed', () => {
  for (const zone of ['', 'Invalid/Zone']) {
    assert.equal(validTimeZone(zone), false);
    const time = corporateTime('2026-11-16T11:49:59Z', zone);
    assert.equal(time.timeZone, 'UTC');
    assert.ok(time.local.includes('11:49:59'));
  }
  for (const value of ['', 'yesterday', '2026-11-16', '2026-13-16T11:49:59Z']) {
    assert.equal(corporateTime(value, 'America/Mexico_City'), null);
  }
});

test('visit card and audit display site time plus exact UTC, including pending movements', () => {
  const component = ts.transpileModule(fs.readFileSync('src/app/dashboard/corporativo/visitas/CorporateVisitsClient.tsx', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  for (const [zone, local] of [['America/Mexico_City', '05:49:59'], ['Asia/Tokyo', '20:49:59'], ['Invalid/Zone', '11:49:59']]) {
    const states = [{ site: {nombre:'Central', zona_horaria:zone}, caps:{hosts:[]}, destinations:[], visits:[{
      visit_id:'v1', visitor_ref:'TEST', state:'dentro', entered_at:'2026-11-16T11:49:59.009280', exited_at:null,
    }] }, '', false, {}, null, null, {visitId:'v1',entries:[{event_uid:'e1',action:'entrada',timestamp:'2026-11-16T11:49:59.009280'}]}];
    let index = 0;
    const loaded = { exports: {} };
    vm.runInThisContext(`(function(require,module,exports){${component}\n})`)(name => {
      if (name === 'react') return {...React, useState:()=>[states[index++],()=>{}], useEffect:()=>{}};
      if (name === '@clerk/nextjs') return {useAuth:()=>({userId:'fixture',isLoaded:true,getToken:async()=>null})};
      if (name === '@/lib/api') return {api:{}};
      if (name === '@/lib/corporate-time') return mod.exports;
      return require(name);
    }, loaded, loaded.exports);
    const html = renderToStaticMarkup(React.createElement(loaded.exports.default, {tenant:'corp_fixture',site:'site_fixture'}));
    assert.ok(html.includes(local));
    assert.equal((html.match(/UTC: /g)||[]).length, 2, 'card and log both show UTC');
    assert.ok(html.includes('2026-11-16T11:49:59.009280Z'));
    assert.ok(html.includes('Pendiente'));
    if (zone === 'Invalid/Zone') assert.ok(html.includes('zona de sede no válida'));
    else assert.ok(html.includes(zone));
  }
});
