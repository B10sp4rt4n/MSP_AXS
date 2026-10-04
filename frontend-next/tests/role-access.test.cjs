const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

// Execute the real TSX modules with only authentication/network boundaries mocked.
function fixture({ role = 'GUARDIA', userId = 'clerk-guard', token = 'test-token', apiError = false } = {}) {
  const calls = [];
  const cache = new Map();
  function load(relative) {
    const filename = path.resolve(__dirname, '../src', relative);
    if (cache.has(filename)) return cache.get(filename);
    const module = { exports: {} };
    cache.set(filename, module.exports);
    const source = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText;
    const localRequire = (name) => {
      if (name === '@clerk/nextjs/server') return { auth: async () => ({ userId, getToken: async () => token }) };
      if (name === '@clerk/nextjs') return {
        useAuth: () => ({ userId, isLoaded: true, getToken: async () => token }),
        useUser: () => ({ user: null }), UserButton: () => null,
      };
      if (name === 'next/navigation') return { redirect: url => { throw new Error(`redirect:${url}`); } };
      if (name === '@/lib/api') return { api: { get: async (url, value) => {
        calls.push({ url, token: value });
        if (apiError) throw new Error('backend unavailable');
        return { rol: role };
      } } };
      if (name === '@/components/PortalRoleGate') return load('components/PortalRoleGate.tsx');
      if (name === '@/lib/portal-roles') return load('lib/portal-roles.ts');
      return require(name);
    };
    vm.runInThisContext(`(function(require,module,exports){${source}\n})`, { filename })(localRequire, module, module.exports);
    cache.set(filename, module.exports);
    return module.exports;
  }
  async function portal(name) {
    const Layout = load(`app/dashboard/${name}/layout.tsx`).default;
    let mounted = false;
    const Probe = () => { mounted = true; return React.createElement('button', null, 'Acción protegida'); };
    const gate = Layout({ children: React.createElement(Probe) });
    const result = await gate.type(gate.props);
    return { html: renderToStaticMarkup(result), mounted };
  }
  return { portal, load, calls };
}

for (const [role, portal, allowed] of [
  ['GUARDIA', 'admin', false], ['RESIDENTE', 'admin', false],
  ['GUARDIA', 'msp', false], ['ADMIN_CONDOMINIO', 'msp', false],
  ['ADMIN_CONDOMINIO', 'admin', true], ['MSP_ADMIN', 'msp', true],
  ['GUARDIA', 'guardia', true], ['GUARDIA', 'residente', false],
  ['RESIDENTE', 'residente', true], ['RESIDENTE', 'guardia', false],
  ['UNKNOWN', 'admin', false],
]) {
  test(`${role} ${allowed ? 'mounts' : 'cannot mount'} ${portal} controls`, async () => {
    const app = fixture({ role });
    const result = await app.portal(portal);
    assert.equal(result.mounted, allowed);
    assert.equal(result.html.includes('Acción protegida'), allowed);
    if (!allowed) assert.match(result.html, /no tiene permiso/);
    assert.deepEqual(app.calls, [{ url: '/auth/me', token: 'test-token' }]);
  });
}

test('backend failure never mounts administrative controls', async () => {
  const result = await fixture({ role: 'MSP_ADMIN', apiError: true }).portal('admin');
  assert.equal(result.mounted, false);
  assert.match(result.html, /No pudimos comprobar tus permisos/);
});

test('missing token never mounts administrative controls or calls backend', async () => {
  const app = fixture({ role: 'MSP_ADMIN', token: null });
  const result = await app.portal('admin');
  assert.equal(result.mounted, false);
  assert.deepEqual(app.calls, []);
});

test('signed-out visitors redirect before any protected content', async () => {
  const app = fixture({ userId: null });
  await assert.rejects(app.portal('admin'), /redirect:\/sign-in/);
  assert.deepEqual(app.calls, []);
});

test('dashboard never exposes portal links while profile is unresolved', () => {
  const Dashboard = fixture().load('app/dashboard/DashboardClient.tsx').default;
  const html = renderToStaticMarkup(React.createElement(Dashboard));
  assert.match(html, /Comprobando permisos/);
  for (const portal of ['admin', 'msp', 'residente', 'guardia']) {
    assert.equal(html.includes(`href="/dashboard/${portal}"`), false);
  }
});
