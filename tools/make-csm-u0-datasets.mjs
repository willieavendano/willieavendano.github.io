#!/usr/bin/env node
// Generates the Unit 0 mini-project datasets. Every messy feature described in
// the briefs is placed deliberately; only the clean values are randomized, so a
// per-student seed changes the numbers without changing the traps.
//   node tools/make-csm-u0-datasets.mjs                 # write the two base CSVs
//   node tools/make-csm-u0-datasets.mjs --students 24   # + one variant per student
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const resDir = path.join(root, 'computer-science-math', 'resources');

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const randInt = (rng, lo, hi) => lo + Math.floor(rng() * (hi - lo + 1));
const shuffle = (arr, rng) => {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
};
const esc = (s) => {
  s = String(s);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
};
const toCsv = (rows) => rows.map((r) => r.map(esc).join(',')).join('\n') + '\n';

// ---------------------------------------------------------------------------
// Option 2 — The Cafecito Receipt
// ---------------------------------------------------------------------------
const CAFE = [
  ['Cortadito', 2.5],
  ['Colada', 3.0],
  ['Café con Leche', 4.0],
  ['Espresso', 2.25],
  ['Guava Pastelito', 3.5],
  ['Cheese Pastelito', 3.25],
  ['Croqueta', 2.0],
  ['Cuban Sandwich', 8.5],
  ['Empanada', 3.75],
  ['Mamey Batido', 5.5],
  ['Pan con Bistec', 9.0],
  ['Medianoche', 7.5],
];

function cafecito(seed) {
  const rng = mulberry32(seed);
  const chosen = shuffle(CAFE, rng).slice(0, 11);
  const rows = chosen.map(([name, base]) => {
    const price = Math.round((base + (rng() * 0.8 - 0.3)) * 20) / 20;
    return {
      name,
      price: Math.max(1.5, price),
      qty: randInt(rng, 1, 6),
      tip: [0.1, 0.15, 0.18, 0.2, 0.25][randInt(rng, 0, 4)],
    };
  });

  // Deliberate mess, fixed positions.
  rows[0].name += ' ';
  rows[0].price = `$${rows[0].price.toFixed(2)}`; // text price
  rows[1].name = rows[1].name.toUpperCase();      // inconsistent case
  rows[5].price = `€${rows[5].price.toFixed(2)}`; // euro row
  rows[6].name += ' ';
  rows[7].price = `$${rows[7].price.toFixed(2)}`; // text price
  rows[8].qty = '';                               // blank quantity
  rows[9].name += ' ';

  const body = rows.map((r) => [r.name, r.price, r.qty, r.tip]);
  body.push([...body[4]]); // duplicated row
  return toCsv([['Item', 'Price', 'Qty', 'Tip %'], ...body]);
}

// ---------------------------------------------------------------------------
// Option 3 — The Cold Snap
// ---------------------------------------------------------------------------
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const pad = (n) => String(n).padStart(2, '0');
const FMT = [
  (d) => `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`,
  (d) => `${d.getUTCMonth() + 1}/${d.getUTCDate()}/${String(d.getUTCFullYear()).slice(2)}`,
  (d) => `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`,
  (d) => `${d.getUTCMonth() + 1}/${d.getUTCDate()}/${d.getUTCFullYear()}`,
  (d) => `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`,
  (d) => `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`,
];

function coldSnap(seed) {
  const rng = mulberry32(seed);
  const startDay = randInt(rng, 3, 12); // still early January
  const start = new Date(Date.UTC(2026, 0, startDay));
  const highBase = [78, 75, 73, 70, 68, 65, 60, 55, 50, 46, 42, 38, 36, 35];
  const lowBase = [62, 60, 58, 56, 54, 50, 46, 42, 38, 34, 30, 28, 26, 24];

  const rows = highBase.map((h, i) => ({
    date: new Date(start.getTime() + i * 86400000),
    fmt: FMT[i % FMT.length],
    high: h + randInt(rng, -2, 2),
    low: lowBase[i] + randInt(rng, -2, 2),
    note: '',
  }));

  // Deliberate mess, fixed positions.
  rows[4].high = `${rows[4].high}F`;        // text temperature
  rows[9].low = `${rows[9].low}F`;          // text temperature
  rows[5].high = 18; rows[5].low = 10; rows[5].note = 'sensor reset'; // actually °C
  rows[7].high = 212;                        // impossible value
  rows[10].high = ''; rows[10].low = ''; rows[10].note = 'station down'; // blank day
  rows[11].high = 3; rows[11].low = -2; rows[11].note = 'check units';   // actually °C

  const body = rows.map((r) => [r.fmt(r.date), r.high, r.low, r.note]);
  return toCsv([['Date', 'High (°F)', 'Low (°F)', 'Notes'], ...body]);
}

// ---------------------------------------------------------------------------
function write(rel, text) {
  fs.mkdirSync(path.dirname(rel), { recursive: true });
  fs.writeFileSync(rel, text);
  console.log(`wrote ${path.relative(root, rel)}`);
}

const args = process.argv.slice(2);
const studentsIdx = args.indexOf('--students');
const students = studentsIdx >= 0 ? parseInt(args[studentsIdx + 1], 10) : 0;
const base = studentsIdx >= 0 ? parseInt(args[args.indexOf('--seed') + 1] || '1', 10) : 1;

write(path.join(resDir, 'csm-u0-cafecito-receipt.csv'), cafecito(base));
write(path.join(resDir, 'csm-u0-cold-snap.csv'), coldSnap(base + 1000));

if (students > 0) {
  const out = path.join(resDir, 'u0-datasets');
  for (let i = 1; i <= students; i++) {
    const tag = `s${pad(i)}`;
    write(path.join(out, `csm-u0-cafecito-receipt-${tag}.csv`), cafecito(base + i * 17));
    write(path.join(out, `csm-u0-cold-snap-${tag}.csv`), coldSnap(base + 1000 + i * 17));
  }
  console.log(`\n${students} student variants written to computer-science-math/resources/u0-datasets/`);
}