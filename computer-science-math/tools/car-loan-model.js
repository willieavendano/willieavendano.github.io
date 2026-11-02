/* Car loan model — the arithmetic behind car-loan-calculator.html.
 *
 * Deliberately dependency-free and usable two ways:
 *   1. <script src="car-loan-model.js"> in the page, which defines window.CarLoanModel.
 *   2. require('./car-loan-model.js') in Node, for the tests in tests/.
 *
 * Conventions that matter for students:
 *   - "rate" is the nominal annual *contract* interest rate in percent,
 *     compounded monthly as rate / 12 / 100. It is not an APY and it is not
 *     necessarily the APR a lender quotes (APR can include fees).
 *   - Every schedule row is computed at full floating-point precision.
 *     Rounding happens only when a value is formatted for display.
 *   - The final payment is clamped so the closing balance lands exactly on
 *     zero. Without that clamp the last row can be off by a cent or drift
 *     negative for long terms.
 */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.CarLoanModel = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var MAX_RATE = 100;
  var MAX_MONTHS = 120;

  /** Parse a number the way a student might type it. Returns NaN when unusable. */
  function toNumber(value) {
    if (typeof value === 'number') return Number.isFinite(value) ? value : NaN;
    if (typeof value !== 'string') return NaN;
    var text = value.trim().replace(/[,\s$]/g, '');
    if (text === '') return NaN; // Number('') is 0, which would silently pass validation.
    var n = Number(text);
    return Number.isFinite(n) ? n : NaN;
  }

  function money(n) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(n);
  }

  /** Equal monthly payment for principal P, nominal annual rate in percent, n months. */
  function monthlyPayment(principal, annualRatePct, months) {
    if (!(months > 0)) return 0;
    if (!(principal > 0)) return 0;
    var r = annualRatePct / 1200;
    if (r === 0) return principal / months;
    // log1p/expm1 preserve precision when a positive rate is very close to zero.
    return principal * (r / -Math.expm1(-months * Math.log1p(r)));
  }

  /**
   * Full amortization schedule at full precision.
   * Row: { month, opening, payment, interest, principal, closing, cumulativeInterest }
   * The last row's principal is clamped to the opening balance so closing === 0.
   */
  function buildSchedule(principal, annualRatePct, months) {
    var payment = monthlyPayment(principal, annualRatePct, months);
    var r = annualRatePct / 1200;
    var rows = [];
    var balance = principal > 0 ? principal : 0;
    var cumulativeInterest = 0;

    for (var month = 1; month <= months && balance > 0; month++) {
      var opening = balance;
      var interest = opening * r;
      var principalPaid = payment - interest;
      // Final-row (and float-drift) clamp: never repay more principal than is owed.
      if (principalPaid > opening || month === months) principalPaid = opening;
      if (principalPaid < 0) principalPaid = 0; // Defensive: only reachable with bad inputs.
      var thisPayment = principalPaid + interest;
      balance = opening - principalPaid;
      if (balance < 1e-9) balance = 0;
      cumulativeInterest += interest;
      rows.push({
        month: month,
        opening: opening,
        payment: thisPayment,
        interest: interest,
        principal: principalPaid,
        closing: balance,
        cumulativeInterest: cumulativeInterest
      });
    }

    var totalPaid = 0;
    for (var i = 0; i < rows.length; i++) totalPaid += rows[i].payment;

    return {
      rows: rows,
      payment: rows.length ? payment : 0,
      totalInterest: cumulativeInterest,
      totalPaid: totalPaid,
      months: months
    };
  }

  /**
   * Validate raw form values. Returns { ok, errors, values }.
   * errors is keyed by field so the page can mark each input and describe it.
   */
  function validate(raw) {
    var errors = {};
    var price = toNumber(raw.price);
    var fees = toNumber(raw.fees);
    var down = toNumber(raw.down);
    var rate = toNumber(raw.rate);
    var months = toNumber(raw.months);
    var otd = 0;

    if (!Number.isFinite(price)) {
      errors.price = isEmpty(raw.price)
        ? 'Enter the car’s listed price.'
        : 'Enter a number for the listed price, such as 15000.';
    } else if (price < 0) {
      errors.price = 'Listed price cannot be negative.';
    }

    if (!Number.isFinite(fees)) {
      errors.fees = isEmpty(raw.fees)
        ? 'Enter taxes and fees, or 0 if there are none.'
        : 'Enter a number for taxes and fees, such as 1000.';
    } else if (fees < 0) {
      errors.fees = 'Taxes and fees cannot be negative.';
    }

    if (!errors.price && !errors.fees) {
      otd = price + fees;
      if (!Number.isFinite(otd) || otd > Number.MAX_SAFE_INTEGER / 100) {
        errors.price = 'Enter a smaller purchase amount that can be represented accurately in cents.';
      } else if (otd <= 0) {
        errors.price = 'Enter a purchase price greater than $0. A listed price plus taxes and fees must be more than zero.';
      }
    }

    if (!Number.isFinite(down)) {
      errors.down = isEmpty(raw.down)
        ? 'Enter a down payment, or 0 if you are financing the whole price.'
        : 'Enter a number for the down payment, such as 4302.33.';
    } else if (down < 0) {
      errors.down = 'Down payment cannot be negative.';
    } else if (otd > 0 && down > otd + 1e-9) {
      errors.down = 'Down payment cannot be more than the ' + money(otd) +
        ' out-the-door price. Lower the down payment or raise the price and fees.';
    }

    if (!Number.isFinite(rate)) {
      errors.rate = isEmpty(raw.rate)
        ? 'Enter the annual contract interest rate, or 0 for no interest.'
        : 'Enter a number for the interest rate, such as 7 or 7.5.';
    } else if (rate < 0) {
      errors.rate = 'Interest rate cannot be negative.';
    } else if (rate > MAX_RATE) {
      errors.rate = 'Enter a rate of ' + MAX_RATE + '% or less.';
    }

    if (!Number.isFinite(months)) {
      errors.months = isEmpty(raw.months)
        ? 'Enter a term in whole months, such as 60.'
        : 'Enter the term as a number of months, such as 60.';
    } else if (Math.floor(months) !== months) {
      errors.months = 'Term must be a whole number of months.';
    } else if (months < 1) {
      errors.months = 'Term must be at least 1 month.';
    } else if (months > MAX_MONTHS) {
      errors.months = 'Term must be ' + MAX_MONTHS + ' months (10 years) or less.';
    }

    var ok = Object.keys(errors).length === 0;
    return {
      ok: ok,
      errors: errors,
      values: {
        price: price,
        fees: fees,
        otd: otd,
        down: down,
        rate: rate,
        months: months,
        loanAmount: ok ? otd - down : NaN
      }
    };
  }

  function isEmpty(value) {
    return value === undefined || value === null || String(value).trim() === '';
  }

  /** Everything the results panel needs, from already-validated values. */
  function summarize(values) {
    var otd = values.price + values.fees;
    var down = values.down;
    var loanAmount = Math.max(0, otd - down);
    var schedule = buildSchedule(loanAmount, values.rate, values.months);
    var totalInterest = schedule.totalInterest;
    var financedCost = loanAmount + totalInterest;

    return {
      price: values.price,
      fees: values.fees,
      otd: otd,
      downPayment: down,
      loanAmount: loanAmount,
      monthlyPayment: schedule.payment,
      months: values.months,
      rate: values.rate,
      totalInterest: totalInterest,
      totalPayments: schedule.totalPaid,
      financedCost: financedCost,
      totalCost: down + financedCost,
      downPct: otd > 0 ? down / otd : 0,
      interestPctOfLoan: loanAmount > 0 ? totalInterest / loanAmount : 0,
      interestPctOfOtd: otd > 0 ? totalInterest / otd : 0,
      rows: schedule.rows,
      first: schedule.rows[0] || null,
      last: schedule.rows.length ? schedule.rows[schedule.rows.length - 1] : null
    };
  }

  /**
   * Compare the same price, down payment and rate across terms.
   * Only the term changes, so monthly payment and total interest are
   * directly comparable — that is the whole point of the table.
   */
  function compareTerms(values, terms) {
    var otd = values.price + values.fees;
    var loanAmount = Math.max(0, otd - values.down);
    var list = (terms || [36, 48, 60, 72, 84]).slice();
    if (list.indexOf(values.months) === -1) list.push(values.months);
    list.sort(function (a, b) { return a - b; });

    return list.map(function (months) {
      var schedule = buildSchedule(loanAmount, values.rate, months);
      return {
        months: months,
        payment: schedule.payment,
        totalInterest: schedule.totalInterest,
        totalCost: values.down + loanAmount + schedule.totalInterest,
        financedCost: loanAmount + schedule.totalInterest,
        selected: months === values.months
      };
    });
  }

  /** Year-end aggregates for the summary schedule view. */
  function yearlySummary(rows) {
    var years = [];
    for (var i = 0; i < rows.length; i += 12) {
      var chunk = rows.slice(i, i + 12);
      var interest = 0;
      var principal = 0;
      var paid = 0;
      for (var j = 0; j < chunk.length; j++) {
        interest += chunk[j].interest;
        principal += chunk[j].principal;
        paid += chunk[j].payment;
      }
      years.push({
        year: years.length + 1,
        firstMonth: chunk[0].month,
        lastMonth: chunk[chunk.length - 1].month,
        payments: chunk.length,
        interest: interest,
        principal: principal,
        paid: paid,
        closing: chunk[chunk.length - 1].closing,
        cumulativeInterest: chunk[chunk.length - 1].cumulativeInterest
      });
    }
    return years;
  }

  /** CSV of the full schedule, cents-rounded for a spreadsheet. */
  function toCSV(summary) {
    var head = ['Payment', 'Opening balance', 'Payment amount', 'Interest', 'Principal', 'Closing balance', 'Cumulative interest'];
    var lines = [head.join(',')];
    summary.rows.forEach(function (row) {
      lines.push([
        row.month,
        row.opening.toFixed(2),
        row.payment.toFixed(2),
        row.interest.toFixed(2),
        row.principal.toFixed(2),
        row.closing.toFixed(2),
        row.cumulativeInterest.toFixed(2)
      ].join(','));
    });
    return lines.join('\r\n') + '\r\n';
  }

  return {
    MAX_RATE: MAX_RATE,
    MAX_MONTHS: MAX_MONTHS,
    toNumber: toNumber,
    money: money,
    monthlyPayment: monthlyPayment,
    buildSchedule: buildSchedule,
    validate: validate,
    summarize: summarize,
    compareTerms: compareTerms,
    yearlySummary: yearlySummary,
    toCSV: toCSV
  };
});
