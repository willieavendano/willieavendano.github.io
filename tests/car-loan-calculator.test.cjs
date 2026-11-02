// Tests for the car-loan calculator model and page.
// Model tests run in Node with no dependencies:
//   node --test tests/car-loan-calculator.test.cjs
// The page-level checks are in car-loan-calculator.dom.test.cjs (needs Playwright).
const { test } = require('node:test');
const assert = require('node:assert/strict');

const M = require('../computer-science-math/tools/car-loan-model.js');

const CLOSE = (a, b, eps = 1e-6) => Math.abs(a - b) <= eps;

test('very small positive rates approach the zero-rate payment', () => {
  assert.ok(CLOSE(M.monthlyPayment(12000, 1e-15, 60), 200));
  const s = M.buildSchedule(12000, 1e-15, 60);
  assert.ok(Number.isFinite(s.totalPaid));
  assert.equal(s.rows.at(-1).closing, 0);
});

test('purchase totals outside reliable cent precision are rejected', () => {
  for (const price of [1e308, Number.MAX_SAFE_INTEGER]) {
    const v = M.validate({ price, fees: price, down: 0, rate: 7, months: 60 });
    assert.equal(v.ok, false);
    assert.ok(v.errors.price);
  }
});

test('zero rate divides the principal evenly', () => {
  assert.equal(M.monthlyPayment(12000, 0, 60), 200);
  const s = M.buildSchedule(12000, 0, 60);
  assert.equal(s.rows.length, 60);
  assert.ok(s.rows.every((r) => r.interest === 0));
  assert.ok(CLOSE(s.totalInterest, 0));
  assert.equal(s.rows.at(-1).closing, 0);
});

test('payment matches the closed-form amortization formula', () => {
  // HYSA sample: $16,000 out-the-door, $4,302.33 down, 7%, 60 months.
  const principal = 16000 - 4302.33;
  const paid = M.monthlyPayment(principal, 7, 60);
  assert.ok(CLOSE(paid, 231.6278861295, 1e-9), `got ${paid}`);

  const s = M.buildSchedule(principal, 7, 60);
  assert.equal(M.money(s.payment), '$231.63');
  assert.ok(CLOSE(s.totalInterest, 2200.003168, 1e-5), `interest ${s.totalInterest}`);
  assert.equal(M.money(s.totalInterest), '$2,200.00');
});

test('every schedule repays exactly the principal and ends at zero', () => {
  for (const [p, rate, n] of [[11697.67, 7, 60], [11697.67, 7, 72], [25000, 4.5, 36], [1, 19.99, 1], [1e6, 19.99, 120]]) {
    const s = M.buildSchedule(p, rate, n);
    const principalSum = s.rows.reduce((sum, r) => sum + r.principal, 0);
    assert.ok(CLOSE(principalSum, p, 1e-6 * Math.max(1, p)), `principal sum ${principalSum} vs ${p}`);
    assert.equal(s.rows.at(-1).closing, 0);
    assert.equal(s.rows.length, n);
    assert.ok(s.rows.every((r) => r.principal >= 0 && r.interest >= 0), 'no negative splits');
    // Every non-final row pays the level payment; the last row is clamped.
    for (let i = 0; i < s.rows.length - 1; i++) {
      assert.ok(CLOSE(s.rows[i].payment, s.payment, 1e-9), `row ${i + 1} payment drift`);
    }
  }
});

test('final payment is clamped, never a stray cent or overpayment', () => {
  const s = M.buildSchedule(10000, 5.9, 60);
  const last = s.rows.at(-1);
  assert.ok(last.payment <= s.payment + 1e-9);
  assert.ok(CLOSE(s.totalPayments ?? s.totalPaid, s.totalPaid));
  // Total of payments equals principal plus interest, to floating point.
  assert.ok(CLOSE(s.totalPaid, 10000 + s.totalInterest, 1e-7));
});

test('zero principal produces no schedule and no payment', () => {
  const s = M.buildSchedule(0, 7, 60);
  assert.equal(s.rows.length, 0);
  assert.equal(s.payment, 0);
  assert.equal(s.totalInterest, 0);
  assert.equal(s.totalPaid, 0);
});

test('number parsing accepts classroom input shapes and rejects junk', () => {
  assert.equal(M.toNumber('15000'), 15000);
  assert.equal(M.toNumber(' 1,500 '), 1500);
  assert.equal(M.toNumber('$7'), 7);
  assert.equal(M.toNumber(4302.33), 4302.33);
  assert.ok(Number.isNaN(M.toNumber('')));
  assert.ok(Number.isNaN(M.toNumber('   ')));
  assert.ok(Number.isNaN(M.toNumber('abc')));
  assert.ok(Number.isNaN(M.toNumber('4.5%')));
  assert.ok(Number.isNaN(M.toNumber(Infinity)));
  assert.ok(Number.isNaN(M.toNumber(NaN)));
  assert.ok(Number.isNaN(M.toNumber(null)));
});

test('validation accepts the sample car', () => {
  const v = M.validate({ price: '15000', fees: '1000', down: '4302.33', rate: '7', months: '60' });
  assert.deepEqual(v.errors, {});
  assert.equal(v.ok, true);
  assert.equal(v.values.otd, 16000);
  assert.ok(CLOSE(v.values.loanAmount, 11697.67));
});

test('validation rejects bad money, bad term, and down payment above price', () => {
  const cases = [
    [{ price: '-1', fees: '0', down: '0', rate: '5', months: '60' }, 'price'],
    [{ price: '', fees: '0', down: '0', rate: '5', months: '60' }, 'price'],
    [{ price: '0', fees: '0', down: '0', rate: '5', months: '60' }, 'price'],
    [{ price: '15000', fees: '-100', down: '0', rate: '5', months: '60' }, 'fees'],
    [{ price: '15000', fees: '1000', down: '-1', rate: '5', months: '60' }, 'down'],
    [{ price: '15000', fees: '1000', down: '17000', rate: '5', months: '60' }, 'down'],
    [{ price: '15000', fees: '1000', down: '0', rate: '-1', months: '60' }, 'rate'],
    [{ price: '15000', fees: '1000', down: '0', rate: '101', months: '60' }, 'rate'],
    [{ price: '15000', fees: '1000', down: '0', rate: '5', months: '0' }, 'months'],
    [{ price: '15000', fees: '1000', down: '0', rate: '5', months: '60.5' }, 'months'],
    [{ price: '15000', fees: '1000', down: '0', rate: '5', months: '121' }, 'months'],
    [{ price: '15000', fees: '1000', down: '0', rate: '5', months: 'abc' }, 'months']
  ];
  for (const [raw, field] of cases) {
    const v = M.validate(raw);
    assert.equal(v.ok, false, `expected invalid: ${JSON.stringify(raw)}`);
    assert.ok(v.errors[field], `expected ${field} error, got ${JSON.stringify(v.errors)}`);
  }
});

test('down payment may equal the out-the-door price but not exceed it', () => {
  const equal = M.validate({ price: '15000', fees: '1000', down: '16000', rate: '7', months: '60' });
  assert.equal(equal.ok, true);
  assert.equal(equal.values.loanAmount, 0);

  const over = M.validate({ price: '15000', fees: '1000', down: '16000.01', rate: '7', months: '60' });
  assert.equal(over.ok, false);
  assert.match(over.errors.down, /out-the-door/);
  assert.match(over.errors.down, /\$16,000\.00/);
});

test('summary separates purchase cost from financing cost', () => {
  const v = M.validate({ price: '15000', fees: '1000', down: '4302.33', rate: '7', months: '60' });
  const s = M.summarize(v.values);
  assert.equal(M.money(s.otd), '$16,000.00');
  assert.equal(M.money(s.loanAmount), '$11,697.67');
  assert.equal(M.money(s.monthlyPayment), '$231.63');
  assert.equal(M.money(s.totalInterest), '$2,200.00');
  // Purchase + financing = down payment + amount financed + interest.
  assert.ok(CLOSE(s.totalCost, 4302.33 + s.loanAmount + s.totalInterest, 1e-9));
  assert.equal(M.money(s.totalCost), '$18,200.00');
  assert.ok(CLOSE(s.downPct, 4302.33 / 16000, 1e-12));
  assert.equal(s.rows.length, 60);
  assert.equal(s.first.month, 1);
  assert.equal(s.last.closing, 0);
});

test('zero-interest summary has no interest and a flat split', () => {
  const v = M.validate({ price: '15000', fees: '1000', down: '4000', rate: '0', months: '24' });
  const s = M.summarize(v.values);
  assert.equal(M.money(s.monthlyPayment), '$500.00');
  assert.equal(s.totalInterest, 0);
  assert.ok(s.rows.every((r) => r.interest === 0 && CLOSE(r.principal, 500)));
});

test('cash purchase summary is all zeros, not NaN', () => {
  const v = M.validate({ price: '15000', fees: '1000', down: '16000', rate: '7', months: '60' });
  const s = M.summarize(v.values);
  assert.equal(s.loanAmount, 0);
  assert.equal(s.monthlyPayment, 0);
  assert.equal(s.totalInterest, 0);
  assert.equal(s.totalCost, 16000);
  assert.equal(s.rows.length, 0);
  assert.equal(s.last, null);
  assert.ok(Number.isFinite(s.interestPctOfLoan));
});

test('term comparison holds price, down payment and rate constant', () => {
  const v = M.validate({ price: '15000', fees: '1000', down: '4302.33', rate: '7', months: '60' });
  const rows = M.compareTerms(v.values);
  assert.deepEqual(rows.map((r) => r.months), [36, 48, 60, 72, 84]);
  const sixty = rows.find((r) => r.months === 60);
  const seventyTwo = rows.find((r) => r.months === 72);
  assert.ok(sixty.selected && !seventyTwo.selected);
  assert.equal(M.money(sixty.payment), '$231.63');
  assert.equal(M.money(sixty.totalInterest), '$2,200.00');
  assert.equal(M.money(seventyTwo.payment), '$199.43');
  assert.equal(M.money(seventyTwo.totalInterest), '$2,661.55');
  assert.ok(seventyTwo.payment < sixty.payment, 'longer term lowers the payment');
  assert.ok(seventyTwo.totalInterest > sixty.totalInterest, 'longer term costs more interest');
  assert.ok(seventyTwo.totalCost > sixty.totalCost);
  // A non-standard term is added once and stays sorted.
  const withCustom = M.compareTerms(v.values, [36, 72]);
  assert.deepEqual(withCustom.map((r) => r.months), [36, 60, 72]);
});

test('yearly summary reconciles with the monthly schedule', () => {
  const v = M.validate({ price: '15000', fees: '1000', down: '4302.33', rate: '7', months: '60' });
  const s = M.summarize(v.values);
  const years = M.yearlySummary(s.rows);
  assert.equal(years.length, 5);
  assert.equal(years.map((y) => y.payments).join(','), '12,12,12,12,12');
  assert.ok(CLOSE(years.reduce((a, y) => a + y.interest, 0), s.totalInterest, 1e-9));
  assert.ok(CLOSE(years.reduce((a, y) => a + y.principal, 0), s.loanAmount, 1e-6));
  assert.equal(years.at(-1).closing, 0);
  // A 61-month loan has a 1-payment final year.
  const odd = M.buildSchedule(10000, 6, 61);
  assert.equal(M.yearlySummary(odd.rows).at(-1).payments, 1);
});

test('CSV export has one row per payment and closing balance of 0.00', () => {
  const v = M.validate({ price: '15000', fees: '1000', down: '4302.33', rate: '7', months: '60' });
  const csv = M.toCSV(M.summarize(v.values));
  const lines = csv.trim().split('\r\n');
  assert.equal(lines.length, 61);
  assert.equal(lines[0], 'Payment,Opening balance,Payment amount,Interest,Principal,Closing balance,Cumulative interest');
  assert.equal(lines[1].split(',')[0], '1');
  assert.match(lines.at(-1), /,0\.00,2\d{3}\.\d\d$/);
});

test('money formats to cents with group separators', () => {
  assert.equal(M.money(231.6278861295), '$231.63');
  assert.equal(M.money(0), '$0.00');
  assert.equal(M.money(1234567.891), '$1,234,567.89');
});
