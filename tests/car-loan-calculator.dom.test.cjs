// DOM and interaction checks for the car-loan calculator page.
//
// Requires Playwright (not a repo dependency — run from a scratch install):
//   NODE_PATH=/tmp/pw-verify/node_modules node --test tests/car-loan-calculator.dom.test.cjs
//
// If Playwright's bundled browser download is missing but a cached Chromium
// exists, point at it explicitly:
//   CHROMIUM_PATH=~/Library/Caches/ms-playwright/chromium_headless_shell-1228/\
//     chrome-headless-shell-mac-arm64/chrome-headless-shell
//
// Serves the page from file:// with no build step and no dev server.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const PAGE = 'file://' + path.join(__dirname, '..', 'computer-science-math', 'tools', 'car-loan-calculator.html');

let chromium;
try { ({ chromium } = require('playwright')); } catch { /* handled below */ }

const hasPlaywright = Boolean(chromium);
const skip = hasPlaywright ? false : 'playwright not installed (see header)';
const executablePath = process.env.CHROMIUM_PATH || undefined;

let browser;
let page;

before(async () => {
  if (!hasPlaywright) return;
  browser = await chromium.launch(executablePath ? { executablePath } : {});
  page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
  page.on('pageerror', (e) => { throw new Error('page error: ' + e.message); });
  await page.goto(PAGE);
  await page.waitForSelector('#result-body:not([hidden])');
});

after(async () => { if (browser) await browser.close(); });

const text = (sel) => page.textContent(sel).then((t) => t.replace(/\s+/g, ' ').trim());
const set = async (id, value) => {
  await page.fill('#' + id, String(value));
  await page.dispatchEvent('#' + id, 'input');
  await page.waitForTimeout(60);
};

test('sample car renders the expected sample numbers', { skip }, async () => {
  assert.equal(await text('#r-payment'), '$231.63');
  assert.equal(await text('#otd'), '$16,000.00');
  const stats = await text('#r-stats');
  assert.match(stats, /\$11,697\.67/);   // amount financed
  assert.match(stats, /\$2,200\.00/);    // total interest
  assert.match(stats, /\$18,200\.00/);   // purchase + financing
  const caption = await text('#bar-caption');
  assert.match(caption, /\$16,000\.00/);
  assert.match(caption, /14\./.test(caption) ? /14\./ : /13\.8/); // interest ≈ 13.75% of OTD
});

test('headline payment and term labels carry units', { skip }, async () => {
  await set('f-months', 60);
  const sub = await text('#r-payment-sub');
  assert.match(sub, /per month/);
  assert.match(sub, /60 payments/);
  const stats = await text('#r-stats');
  assert.match(stats, /out-the-door/i);
});

test('60 vs 72 months: payment down, total cost up', { skip }, async () => {
  await set('f-months', 60);
  const sixty = {
    payment: await text('#r-payment'),
    stats: await text('#r-stats')
  };
  await set('f-months', 72);
  const seventyTwo = {
    payment: await text('#r-payment'),
    stats: await text('#r-stats')
  };
  assert.equal(sixty.payment, '$231.63');
  assert.equal(seventyTwo.payment, '$199.43');
  assert.match(sixty.stats, /\$2,200\.00/);
  assert.match(seventyTwo.stats, /\$2,661\.55/);

  const table = await text('#term-table');
  assert.match(table, /your term/);
  assert.match(table, /72 mo/);
  assert.match(table, /60 mo/);
  // The insight is written around the student's own term, and names both
  // directions: shorter costs more per month, longer costs more overall.
  const insight = await text('#term-insight');
  assert.match(insight, /Your 72-month loan/);
  assert.match(insight, /36 months/);
  assert.match(insight, /84 months/);
  await set('f-months', 60);
});

test('term comparison rows are marked on the selected term only', { skip }, async () => {
  await set('f-months', 60);
  const selected = await page.$$eval('#term-body tr.is-selected', (rows) => rows.map((r) => r.textContent.trim()));
  assert.equal(selected.length, 1);
  assert.match(selected[0], /60 mo/);
  const pressed = await page.$$eval('.chip[data-term][aria-pressed="true"]', (b) => b.map((x) => x.textContent));
  assert.deepEqual(pressed, ['60']);
});

test('zero rate: payment divides evenly and interest is genuinely zero', { skip }, async () => {
  await set('f-rate', 0);
  await set('f-down', 4000);
  await set('f-months', 24);
  assert.equal(await text('#r-payment'), '$500.00');
  assert.match(await text('#r-stats'), /\$0\.00/);
  assert.match(await text('#insight'), /0%/);
  assert.match(await text('#bar-caption'), /0% rate|adds nothing/);
  await set('f-rate', 7);
  await set('f-down', 4302.33);
  await set('f-months', 60);
});

test('cash purchase does not produce NaN or Infinity', { skip }, async () => {
  await set('f-down', 16000);
  const payment = await text('#r-payment');
  assert.equal(payment, '$0.00');
  const body = await text('#result-body');
  assert.ok(!/NaN|Infinity|undefined/.test(body), 'no NaN/Infinity/undefined in results');
  assert.match(await text('#insight'), /no loan/i);
  assert.match(await text('#sched-body'), /nothing is financed/i);
  assert.equal(await page.isDisabled('#csv-btn'), false);
  await set('f-down', 4302.33);
});

test('invalid input pauses results instead of showing stale numbers', { skip }, async () => {
  await set('f-price', 15000);
  await page.fill('#f-price', '');
  await page.dispatchEvent('#f-price', 'input');
  await page.waitForTimeout(80);
  assert.equal(await page.isVisible('#result-body'), false, 'stale results must be hidden');
  assert.equal(await page.isVisible('#result-empty'), true);
  assert.equal(await page.getAttribute('#f-price', 'aria-invalid'), 'true');
  assert.ok((await text('#e-price')).length > 0, 'price error is described');
  assert.match(await text('#status'), /paused/i);
  assert.equal(await page.isDisabled('#csv-btn'), true);
  await set('f-price', 15000);
  assert.equal(await page.isVisible('#result-body'), true);
});

test('down payment above out-the-door price is blocked with a clear message', { skip }, async () => {
  await set('f-down', 16000.01);
  assert.equal(await page.isVisible('#result-body'), false);
  const msg = await text('#e-down');
  assert.match(msg, /out-the-door/);
  assert.match(msg, /\$16,000\.00/);
  assert.equal(await page.getAttribute('#f-down', 'aria-invalid'), 'true');
  // Equal to the price is allowed (a cash purchase, no loan).
  await set('f-down', 16000);
  assert.equal(await page.isVisible('#result-body'), true);
  await set('f-down', 4302.33);
});

test('term must be a whole positive number of months', { skip }, async () => {
  for (const bad of ['0', '-12', '60.5', '121']) {
    await set('f-months', bad);
    assert.equal(await page.isVisible('#result-body'), false, `months=${bad} should be rejected`);
    assert.ok((await text('#e-months')).length > 0, `months=${bad} has a message`);
  }
  await set('f-months', 60);
  assert.equal(await page.isVisible('#result-body'), true);
});

test('negative money and negative rate are rejected', { skip }, async () => {
  await set('f-price', -1);
  assert.equal(await page.isVisible('#result-body'), false);
  await set('f-price', 15000);

  await set('f-fees', -1);
  assert.equal(await page.isVisible('#result-body'), false);
  await set('f-fees', 1000);

  await set('f-rate', -0.1);
  assert.equal(await page.isVisible('#result-body'), false);
  await set('f-rate', 7);
  assert.equal(await page.isVisible('#result-body'), true);
});

test('schedule ends at exactly zero and reconciles with the summary', { skip }, async () => {
  await set('f-months', 60);
  await page.click('.seg button[data-view="month"]');
  const rows = await page.$$eval('#sched-body tr', (trs) =>
    trs.map((tr) => Array.from(tr.querySelectorAll('th,td')).map((c) => c.textContent.replace(/\s+/g, ' ').trim()))
  );
  assert.equal(rows.length, 60);
  assert.equal(rows.at(-1)[0], '60');
  assert.equal(rows.at(-1)[4], '$0.00', 'closing balance of final payment');

  const nums = (s) => Number(String(s).replace(/[$,+]/g, ''));
  const interestSum = rows.reduce((a, r) => a + nums(r[2]), 0);
  const principalSum = rows.reduce((a, r) => a + nums(r[3]), 0);
  const paidSum = rows.reduce((a, r) => a + nums(r[1]), 0);
  // Each row is displayed rounded to cents, so the three column sums can each
  // land a few cents from the full-precision totals. That is display rounding,
  // disclosed on the page. Anything larger would be a real defect.
  assert.ok(Math.abs(interestSum - 2200.0) < 0.2, `interest rounds to ${interestSum}`);
  assert.ok(Math.abs(principalSum - 11697.67) < 0.2, `principal rounds to ${principalSum}`);
  assert.ok(Math.abs(paidSum - 13897.67) < 0.3, `payments round to ${paidSum}`);

  // What must hold exactly, in every row: the split adds back to the payment.
  for (const r of rows) {
    const [pay, interest, principal] = [nums(r[1]), nums(r[2]), nums(r[3])];
    assert.ok(Math.abs(pay - (interest + principal)) <= 0.011, `row ${r[0]} split off by more than a cent`);
    assert.ok(principal >= 0 && interest >= 0, `row ${r[0]} has a negative split`);
  }

  // The page must disclose that summing rounded cells drifts from the exact
  // total, instead of letting a student think 60 × $231.63 is the truth.
  const note = await text('#rounding-note');
  assert.match(note, /\$13,897\.80/, 'shows the naive rounded product');
  assert.match(note, /\$0\.00/, 'says the balance still closes at zero');

  await page.click('.seg button[data-view="year"]');
  const years = await page.$$eval('#sched-body tr', (trs) => trs.length);
  assert.equal(years, 5);
  assert.match(await text('#sched-body'), /Year 5/);
});

test('CSV download contains one row per payment', { skip }, async () => {
  await set('f-months', 60);
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.click('#csv-btn')
  ]);
  assert.match(download.suggestedFilename(), /car-loan-schedule-60mo\.csv$/);
  const stream = await download.createReadStream();
  let csv = '';
  for await (const chunk of stream) csv += chunk;
  const dataLines = csv.trim().split(/\r?\n/).filter((l) => l && !l.startsWith('#'));
  assert.equal(dataLines.length, 61, 'header + 60 payments');
  assert.match(dataLines[0], /^Payment,Opening balance/);
  assert.match(dataLines.at(-1), /,0\.00,/);
  assert.match(csv, /# Out-the-door price,16000\.00/);
});

test('keyboard: Enter in a field recalculates, chips are buttons', { skip }, async () => {
  await page.focus('#f-months');
  await page.fill('#f-months', '48');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(80);
  assert.equal(await text('#r-payment'), '$280.12');

  await page.click('.chip[data-term="72"]');
  await page.waitForTimeout(60);
  assert.equal(await page.inputValue('#f-months'), '72');
  assert.equal(await text('#r-payment'), '$199.43');
  await page.click('.chip[data-term="60"]');
  await page.waitForTimeout(60);
  assert.equal(await text('#r-payment'), '$231.63');
});

test('every input has a real label and errors are announced', { skip }, async () => {
  const unlabelled = await page.$$eval('input', (els) =>
    els.filter((el) => !el.closest('label') && !document.querySelector(`label[for="${el.id}"]`) && !el.getAttribute('aria-label'))
      .map((el) => el.id)
  );
  assert.deepEqual(unlabelled, [], 'all inputs labelled');
  assert.equal(await page.getAttribute('#status', 'aria-live'), 'polite');
  const described = await page.getAttribute('#f-price', 'aria-describedby');
  assert.match(described, /e-price/);
});

test('blur formats values with thousands separators without breaking the model', { skip }, async () => {
  await page.fill('#f-price', '25000');
  await page.dispatchEvent('#f-price', 'input');
  await page.locator('#f-price').blur();
  await page.waitForTimeout(80);
  assert.equal(await page.inputValue('#f-price'), '25,000');
  assert.equal(await text('#otd'), '$26,000.00');
  // A comma-formatted value still validates and computes.
  const stats = await text('#r-stats');
  assert.ok(!/NaN/.test(stats));
  await set('f-price', 15000);
});

test('blur never rewrites an invalid or precise value', { skip }, async () => {
  // Regression: rounding on blur once turned a 60.5-month term into 61 and
  // cleared the error, silently computing a different loan than the student
  // typed. The value must survive exactly and the error must stay.
  await page.fill('#f-months', '60.5');
  await page.dispatchEvent('#f-months', 'input');
  await page.locator('#f-months').blur();
  await page.waitForTimeout(100);
  assert.equal(await page.inputValue('#f-months'), '60.5', 'invalid term must not be rounded');
  assert.equal(await page.isVisible('#e-months'), true, 'error must still be shown');
  assert.equal(await page.isVisible('#result-body'), false);

  // Extra decimal places on a valid money value are preserved, not rounded.
  await page.fill('#f-price', '15000.567');
  await page.dispatchEvent('#f-price', 'input');
  await page.locator('#f-price').blur();
  await page.waitForTimeout(100);
  assert.equal(await page.inputValue('#f-price'), '15,000.567');

  await set('f-months', 60);
  await set('f-price', 15000);
  assert.equal(await page.isVisible('#result-body'), true);
});

test('reset restores the sample car', { skip }, async () => {
  await set('f-price', 25000);
  await set('f-months', 36);
  await page.click('#reset-btn');
  await page.waitForTimeout(80);
  assert.equal(await page.inputValue('#f-price'), '15000');
  assert.equal(await page.inputValue('#f-months'), '60');
  assert.equal(await page.inputValue('#f-down'), '4302.33');
  assert.equal(await text('#r-payment'), '$231.63');
});

test('no external script hosts and no page errors', { skip }, async () => {
  const hosts = await page.$$eval('script[src], link[rel=stylesheet]', (els) =>
    els.map((el) => new URL(el.src || el.href).host).filter((h) => h && h !== '')
  );
  for (const h of hosts) assert.ok(['fonts.googleapis.com', 'fonts.gstatic.com'].includes(h), `unexpected host ${h}`);
});

test('mobile layout: table scrolls inside its own box, page does not overflow', { skip }, async () => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(120);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  assert.ok(overflow <= 1, `horizontal page overflow of ${overflow}px`);

  const scroller = await page.$eval('#sched-region', (el) => ({
    scrollWidth: el.scrollWidth, clientWidth: el.clientWidth, overflowX: getComputedStyle(el).overflowX
  }));
  assert.ok(['auto', 'scroll'].includes(scroller.overflowX));
  const sticky = await page.$eval('#sched-table thead th', (el) => getComputedStyle(el).position);
  assert.equal(sticky, 'sticky');

  await page.setViewportSize({ width: 1280, height: 1000 });
  await page.waitForTimeout(80);
});


test('cost breakdown retains colored segments on screen and in print', { skip }, async () => {
  await page.click('#reset-btn');
  for (const media of ['screen', 'print']) {
    await page.emulateMedia({ media });
    const segments = await page.locator('#bar .cost-segment').evaluateAll(nodes => nodes.map(n => ({
      color: getComputedStyle(n).backgroundColor,
      display: getComputedStyle(n).display,
      width: n.getBoundingClientRect().width
    })));
    assert.equal(segments.length, 3);
    assert.equal(new Set(segments.map(s => s.color)).size, 3);
    assert.ok(segments.every(s => s.display !== 'none' && s.width > 0 && s.color !== 'rgba(0, 0, 0, 0)'));
  }
  await page.emulateMedia({ media: 'screen' });
});
