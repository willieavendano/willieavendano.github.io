# CS Math — Cornerstone II & III refresh: shared build brief (Nov 16 2026)

Read this whole file before you touch anything. Four agents build in parallel from it; each owns
different files (see "Who builds what"). Never edit a file you do not own.

## Context
CS Math (Computer Science Math) is a project-based Excel-modelling course at The Cushman School,
Miami: 13 high-school students, Period 3. Mon = 40-min single period; Tue/Thu = 80-min blocks.
Course site: class.avendano.xyz, served from this repo (public — never put a real student's
name in any file). Grading is the house 4.0 scale: every criterion is scored 4 / 3 / 2 / 1
(half levels allowed), and the grade is the AVERAGE of the criteria to one decimal. Never points.
Level words: 4 Advanced · 3 Proficient (the expected standard) · 2 Developing · 1 Beginning.
House rules students already know: "The workbook is the work" — formulas, not typed numbers;
every assumption is a labelled input cell; honest rounding (≈ for rounded values, never =).

### New schedule (teacher decision, Nov 16)
- **Cornerstone II — Financing a Car.** Work days: Mon 11/16 (40m), Tue 11/17 (80m), Thu 11/19 (80m).
  Thanksgiving break Nov 23–27. **Workbook + slides due at the start of class Mon 11/30; presentations
  first thing Mon 11/30** (40-minute period, 13 students → a 2-minute talk + ~30 s question each;
  overflow to Tue 12/1). Design so students can finish in class by 11/19; nothing should require break time.
- **Cornerstone III — Personal Budget = the MIDTERM.** Assigned Thu 11/19 (before CS II is presented).
  Work days: Mon 11/30 (after CS II talks), Tue 12/1 (72m), Thu 12/3, Mon 12/7, Tue 12/8, Thu 12/10, Mon 12/14.
  Checkpoints (formative, Ready/Revise): Thu 12/3 baseline budget; Thu 12/10 scenarios draft.
  **Workbook + slides due 8:00 AM Tue 12/15; presentations Tue 12/15 (80-min block, midterm)** →
  4-minute talk + ~1.5-minute live defense each.
- The two cornerstones are ONE pipeline: CS III is built **as new tabs in the same workbook** as CS II, so the
  car payment and ownership costs flow into the budget as live links ("the payment feeds the budget").

### What every student already has (front-loaded)
A **credit profile** (teacher-made, private): job, salary, age, simulated credit score (all Prime, 663–767), tier,
credit history, utilization, late payments, open accounts, and lender APRs for 3/4/5/6/7-year NEW-car loans.
They also got a student workbook ("Financing a $40,000 Car: Your Credit Profile") where they compute the monthly
payment and payment-as-%-of-income for a $36,000 loan ($40,000 price − $4,000 minimum down) at each term.
Rates come from Experian's State of the Automotive Finance Market Q2 2026 tier averages (new: super prime 4.41%,
prime 6.15%, near prime 9.71%; used: prime 8.81%), interpolated by score, ~1 point spread from 36 to 84 months.
Three students' profiles say "self-employed". Salaries $50k–$84k.

## Decisions every deliverable must agree on

### Cornerstone II rules
1. Choose a real car **listed for sale in Miami-Dade County** (dealer or private), out-the-door price **≤ $40,000**.
   Record listing URL, date viewed, and a screenshot; year/make/model/trim, mileage, new or used.
2. Out-the-door (OTD) price is built **by formula**: listed price + Florida sales tax 6% + Miami-Dade surtax 1%
   **on the first $5,000 only** (Florida's discretionary surtax cap for a single item) + dealer fee (Florida has no
   cap; use the listing's or label an assumption, ~$999) + title & registration (label an assumption, ~$400).
3. **Down payment ≥ $4,000** (10% of the $40,000 ceiling — why: depreciation/negative equity, loan-to-value,
   smaller loan = less interest, proof you can save). A cheaper car still needs at least $4,000 down.
   Amount financed = OTD − down payment.
4. Rates come from your credit profile. Those are **new-car** rates. **Used car → add 2.66 percentage points to every
   term** (Experian Q2 2026 prime: new 6.15% vs used 8.81%; class assumption).
5. Build: monthly payment for all five terms (3–7 yr) by formula; total paid, total interest, total cost of the car
   (down + all payments); payment as % of gross monthly income with the lender guideline (<15% comfortable,
   15–20% tight, >20% likely declined) shown by conditional formatting; full amortization schedule for the chosen
   term (final balance ≈ $0.00, Σprincipal = amount financed, Σinterest = total interest); one chart (balance or
   interest vs principal by month), axes labelled, $ axis from 0.
6. **Monthly cost to own** block (feeds CS III): insurance (published Miami average for a 25-year-old, cited — no
   personal quotes), fuel = miles/month ÷ combined mpg (fueleconomy.gov) × $/gal, maintenance, tolls (SunPass).
7. Recommendation: which term you would take and why — payment, total interest, share of income, one limitation.
   Never call the smaller payment "cheaper".
8. Stretch (optional): used-vs-new comparison; 20%-down comparison; Python port of the amortization
   (resources/car_loan_amortization.py) matching to the cent; or HYSA plan that funds the down payment.
9. Presentation (Mon 11/30): **2 minutes, 3 content slides + title**: (1) the car and its OTD build, with the
   listing photo/screenshot and source; (2) the five-loan comparison (table + % of income); (3) the recommendation
   with total cost and one limitation. Then one question — the teacher may change one input live.

### Cornerstone III rules
1. Income: your profile's job and gross salary. Take-home by formula — 2026 federal income tax, single filer,
   **standard deduction $16,100**, brackets 10% to $12,400 · 12% to $50,400 · 22% to $105,700 · 24% to $201,775
   (IRS Rev. Proc. 2025-32); FICA 7.65%; **Florida has no state income tax** (say what that is worth).
   Tax table lives in input cells, not inside formulas.
   **Self-employed profiles:** self-employment tax = net × 92.35% × 15.3% (replaces FICA), half of it is deductible
   before income tax; no employer health plan → marketplace premium (label an assumption, ~$375/mo).
2. Housing: a real **Miami-Dade apartment listing** (URL, date, screenshot, neighborhood, beds/baths, rent). Roommates
   allowed (up to 2 roommates); your share = rent ÷ people unless you state another split. Guideline: housing
   ≤ 30% of gross monthly income — show your %. The repo's 17-neighborhood rent table is a reference, not a source.
3. Spending: **at least 12 categories**, each labelled Fixed or Variable, each with a source or labelled assumption.
   Car payment, insurance, fuel, maintenance, tolls come **by live link from your CS II tabs**.
   Category totals by SUMIF on Fixed/Variable. Savings = take-home − expenses; **savings rate by formula**
   (target ≥ 10%; report the gap if you miss it).
4. Starting emergency fund: a labelled assumption (class default $3,000).
5. Scenarios: baseline + **at least three**, side by side, each changing one thing: one Miami curveball (hurricane
   deductible, car repair on the 826, rent hike at renewal, insurance jump); one good-news case (raise/bonus);
   and **one that breaks the budget** (savings negative), with **months until the emergency fund hits zero**
   computed by formula, and **a stated, modelled fix** (what you cut or change and what it buys you).
   "My budget breaks — here is my fix" is an expected outcome, not a failure. Downgrading the car or adding a
   roommate are legitimate fixes (show the numbers).
6. Charts: where the money goes (one bar per category or stacked); emergency-fund balance over 12 months under the
   baseline and the breaking scenario. Labelled axes, $ from 0.
7. Stretch (optional): compare two neighborhoods including commute cost and time; 401(k) 5% pre-tax; student-loan
   payment scenario; run the 3/5/7-year car loans through the budget.
8. Presentation = **midterm, Tue 12/15: 4 minutes, ~5 content slides** + title: my hand (job, take-home build,
   apartment with photo/screenshot); where the money goes + savings rate; scenarios side by side; the break +
   months to zero + my fix; recommendation + one limitation. Then **live defense (~1.5 min, individual)**: the
   teacher changes one input in the student's workbook (e.g. rent +$200, salary −10%, insurance +$100) and the
   student explains, on the spot, what moved and why, and points at the formula that did it.

### Rubric (both cornerstones; refine the language per project)
Workbook (asset) criteria: **Model Correctness · Formula Honesty · Data Structure · Sources & Assumptions**.
Presentation criteria: **Communication** (slides, chart honesty, conclusion first, time) · **Live Defense**
(explains a formula, predicts/explains a live change).
**Stretch (optional)** counts only if it raises the average. Grade = average of the criteria scored, one decimal.
Each criterion gets four level descriptors (4/3/2/1) written SPECIFICALLY for that project (e.g. CS II Model
Correctness 4 = all five payments, totals and the schedule are right and survive any input change; CS III Model
Correctness 4 = take-home, totals, savings rate, scenarios and months-to-zero are right and survive a live change).
Plus a short "Before you submit" checklist and the Ready/Revise checkpoint criteria for CS III (12/3, 12/10).

## The Level-4 exemplar (fictional student — use these numbers EXACTLY)
Canonical numbers: `docs/csm-cs2-cs3/exemplar-numbers.json` (generated by `exemplar_numbers.py` beside it).
Do not recompute differently, do not round differently, do not invent other figures for anything in that file.
- **Camila Ortiz**, 25, Civil engineer (EIT), W-2, $64,000; score 726, Prime; history 6 yrs, utilization 18%,
  0 late payments, 5 accounts. APRs 3/4/5/6/7 yr: 5.37 / 5.47 / 5.62 / 5.97 / 6.42 %.
- Car: **new 2026 Toyota RAV4 LE Hybrid**, listed $33,950 at a Miami-Dade dealer (**illustrative listing** — say
  so in small print; real students must link a real listing). Sales tax $2,037.00; surtax $50.00 (1% of first
  $5,000); dealer fee $999.00 (assumption); title & registration $400.00 (assumption) → **OTD $37,436.00**.
  Down $5,000 → **financed $32,436.00**. 39 mpg, 1,000 mi/mo, $3.40/gal → fuel $87.18; insurance $310;
  maintenance $50; SunPass $40 → ownership $487.18/mo.
- Loans (payment · total interest · % of gross): 3 yr $977.53 · $2,755.21 · 18.3% | 4 yr $753.90 · $3,751.37 · 14.1% |
  **5 yr $621.36 · $4,845.81 · 11.7% (chosen)** | 6 yr $537.10 · $6,235.13 · 10.1% | 7 yr $480.40 · $7,917.69 · 9.0%.
  5-yr month 1: interest $151.91, principal $469.45. 7-yr costs $3,071.88 more interest than 5-yr.
  Why 5 years (her reasoning): 4-yr is affordable on paper (14.1%) but leaves too little room once rent and insurance
  land; 5-yr is the shortest term under ~12% of gross; 6/7-yr save $84–$141/month but cost $1,389–$3,072 more interest
  and keep her upside-down longer. Limitation: rates are class-model averages and insurance is a published average.
- Budget: take-home $4,467.00/mo (federal tax $5,500.00/yr, FICA $4,896.00/yr; Florida $0). Little Havana 2BR
  listed $2,600 (illustrative), 1 roommate → rent share $1,300 (24.4% of gross). 17 expense lines in the JSON
  totalling $3,531.54 → savings $935.46/mo, **savings rate 20.9%**. Emergency fund start $3,000.
  Scenarios: hurricane (one-time $1,150) → month 1 −$214.54 then back to $935.46; rent +8% → $831.46/mo;
  **hours cut 30% → −$404.64/mo, fund gone in 8 months (breaks)**; her fix (cut eating out $100, entertainment $70,
  pause gym $35, subscriptions $20) → −$179.64/mo, **17 months** of runway; 7-year loan instead → $1,076.42/mo saved
  but $3,071.88 more interest.

## Who builds what (owners)
| Owner | Files (create) |
|---|---|
| Opus (Claude) | `computer-science-math/assignments/cs2-spec.html` + `.pdf`, `cs2-rubric.html` + `.pdf`, `cs3-spec.html` + `.pdf`, `cs3-rubric.html` + `.pdf` |
| GPT-6.1 Sol (Codex) | `tools/make-csm-cs-exemplars.py`, `computer-science-math/resources/csm-cs2-exemplar.xlsx`, `csm-cs3-exemplar.xlsx` |
| GPT-6 Astra (Codex) | `computer-science-math/slides/u2-exemplar-presentation.html` + images under `computer-science-math/slides/img/u2-exemplar/` |
| DeepSeek V4.1 Flash (OpenCode) | `computer-science-math/slides/u3-exemplar-presentation.html` + images under `computer-science-math/slides/img/u3-exemplar/` |
The coordinator (the parent Claude session) owns everything else: calendar/courses.json, csmath-kits.json, kits, READMEs,
course index pages, this brief. Do not edit those. Do not commit or push; leave changes in the working tree.

## House style references (read before building)
- Handouts: `assets/css/handout.css` (layered on `assets/css/syllabus.css`); patterns to match:
  `computer-science-math/assignments/q2-hysa-car-bridge.html` (CS II sample) and `computer-science-math/assignments/casino-lab.html`.
  PDFs: `node tools/build-handout-pdf.mjs <repo-relative.html> <out.pdf>`. Generous write-in space where students write.
- Decks: read `.claude/skills/deck-builder/SKILL.md` in full and follow it (deck.css, pattern decks, notes ≥ 25%,
  ≤ 26 slides, ≈ for rounded values, no answer keys). Exemplar pattern: `computer-science-math/slides/u1-exemplar-presentation.html`
  (written as the student's finished talk, played straight, with teacher notes). Existing CS II lesson decks:
  `computer-science-math/slides/u2-k1…, u2-k2…, u2-k3…`.
- Workbooks: `computer-science-math/resources/csm-u2-exemplars.xlsx` (older 4-level exemplar) and
  `tools/make-csmath-kits.py` (openpyxl builder patterns). Gotcha: cross-sheet refs must be built from recorded row
  numbers, never hard-coded; re-open and assert each ref lands on the intended label.

## Images ("with pictures")
Public school site → only images we may legally publish: Wikimedia Commons (CC0, CC BY, CC BY-SA, public domain),
credited on the slide in small print (title, author, license, "via Wikimedia Commons") and in the notes. No dealer or
listing-site photos, no Google Images, no AI-generated photos passed off as real. Resize to ≤ 1600 px wide and
≤ 350 KB (JPEG/WebP). Charts and spreadsheet views are drawn by you (inline SVG / HTML styled like Excel, with a
formula-bar strip showing the real formula) from the canonical JSON — not screenshots of other sites.
