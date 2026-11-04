// Run against a fresh local lab. Requires Playwright; no runtime app dependency.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({headless: true});
  const context = await browser.newContext();
  const page = await context.newPage();
  const origin = 'http://127.0.0.1:8766';
  const errors = [], external = [];
  page.on('pageerror', e => errors.push(e.message));
  await context.route('**/*', route => {
    if (new URL(route.request().url()).origin !== origin) {
      external.push(route.request().url());
      return route.abort();
    }
    return route.continue();
  });
  const click = async id => { await page.locator(id).click(); await page.waitForFunction(() => !document.querySelector('#entry').disabled); };
  const text = id => page.locator(id).innerText();
  try {
    await page.goto(origin);
    await page.waitForFunction(() => document.querySelector('#state').textContent === 'Visita preparada');
    await page.locator('#credential').fill('wrong');
    await click('#entry');
    assert.match(await text('#message'), /inválido/);
    assert.equal(await page.locator('#retry').isVisible(), false);

    // Commit succeeds in SQLite, but the HTTP response is lost to the browser.
    let loseOperation = true;
    await page.route('**/api/operation', async route => {
      if (!loseOperation) return route.continue();
      loseOperation = false;
      await route.fetch();
      await route.abort();
    });
    await click('#entry');
    assert.equal(await page.locator('#retry').isVisible(), true);
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#state').textContent.includes('Entrada registrada'));
    await click('#retry');
    assert.equal(await page.locator('.event').count(), 1);
    assert.equal(await page.locator('#retry').isVisible(), false);
    await click('#exit');
    assert.equal(await page.locator('.event').count(), 2);

    await click('#lost');
    assert.match(await text('#message'), /confirmación perdida/);
    assert.equal(await text('#pending'), '2');
    await click('#sync');
    assert.equal(await text('#pending'), '0');
    assert.match(await text('#receiver'), /2 movimientos/);
    await click('#sync');
    assert.match(await text('#receiver'), /2 movimientos/);

    await page.locator('#condo').selectOption('B');
    await page.waitForFunction(() => document.querySelector('#state').textContent === 'Visita preparada');
    assert.equal(await page.locator('.event').count(), 0);
    await click('#cancel');
    await click('#entry');
    await click('#exit');
    await click('#sync');
    assert.equal(await text('#conflicts'), '2');
    assert.match(await text('#receiver'), /cancelada/);
    await page.setViewportSize({width: 390, height: 844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    if (process.env.AXS_LAB_SCREENSHOT) await page.screenshot({path: process.env.AXS_LAB_SCREENSHOT, fullPage: true});
    assert.deepEqual(errors, []);
    assert.deepEqual(external, []);
    console.log('PASS browser → localhost API → SQLite → recovery → simulated receiver; two tenants; no external requests; mobile layout.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
