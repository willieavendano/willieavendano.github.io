# CSM-U2-hysa-car-sheets — "Save for the Car: building the model"

Narrated Excel screencast for **Computer Science Math · Cornerstone II** (Q2, in class
Nov 2–5, presentations **Thursday, November 12**). It builds the whole HYSA-bridge workbook
from a blank file — Savings sheet, Loan sheet, 72-month copy, scenario table, ownership
block — and checks every printed handout number on screen as it goes.

- **Script:** `CSM-U2-hysa-car-sheets.tutorial.json` (format: `.claude/skills/screen-tutorial/references/script-format.md`)
- **Source of truth:** `computer-science-math/assignments/q2-hysa-car-bridge.html` (cited below as §1–§11).
  Explanations and traps follow Decks I–III (`computer-science-math/slides/u2-k1…`, `u2-k2…`, `u2-k3…`).
- **Stage:** Excel, window 1600×1000, zoom 160, sheets `Savings`, `Loan` (the script creates `Loan72` and `Compare` itself).

## Published as four parts

The 20-minute single take was split on 2026-11-04 (chapters are unchanged; `parts` in the script group them). Each part opens with a one-line "where we are" and hands off to the next. Build all four with `--all-parts` (or one with `--part p2`); outputs are `out/CSM-U2-hysa-car-sheets-p1.mp4` … `-p4.mp4`, each with its own `.srt`, checks and contact sheets.

| Part | Chapters | Runtime (clone voice) | Students should have beforehand |
|---|---|---|---|
| p1 Savings sheet: inputs and the monthly rate | 0, 1 | ≈ 3:35 | nothing |
| p2 Savings schedule, checks and chart | 2 | ≈ 5:00 | Savings!A2:B7 from p1 |
| p3 Loan sheet: payment and amortization | 3, 4 | ≈ 6:00 | finished Savings sheet (B8 ending balance) |
| p4 60 vs 72 months, ownership costs, Ready or Revise | 5, 6 | ≈ 5:20 | finished Loan sheet with amortization |

Every part burns a step caption into the bottom of the frame for each action the narrator describes (`A3 ← APY`, `Format B6 as 0.00000%`, `Fill down A12:F12 → A13:F71 (⌘D)`, `Insert line chart: …`), so a student can follow with the sound off. The `.srt` stays narration-only. Narration is Willie's ElevenLabs clone with the delivery direction in `videos/manim/voice.env`; function names are written in lowercase in `say` ("if", "sum", "index", "min", "P M T") so the voice reads them as words, with the real spelling kept in `caption`.

## Chapters and runtime

Estimate = spoken words ÷ 2.9 words/s, or the on-screen action time when that is longer
(`estimate_seconds` from `scripts/drivers/base.py`, with `at` pacing), plus a 0.6 s breath per scene.

| # | Chapter | Scenes | Words | Est. time | What happens |
|---|---|---:|---:|---:|---|
| 0 | What we're building | 4 | 148 | 0:53 | Hook (the $16,000 car), two-sheet plan, layout: labels in A, inputs in B, formulas point at inputs (Formula Honesty), fictional values |
| 1 | Savings inputs + monthly rate | 10 | 351 | 2:07 | B2 initial savings, B3 APY (from the bank's disclosure; **callout: type 4.5%**), B4 deposit (end of month), B5 months (reporting month), B7 target; B6 `=(1+B3)^(1/12)-1` and why it's a 12th root; **callout: 12th root, not ÷ 12** |
| 2 | Savings schedule, checks, chart | 22 | 736 | 4:27 | Row 10 headers; row 11 month 0; row 12 cell by cell; end-of-month deposit; hand check $651.84; APY ÷ 12 shown live ($651.88) and fixed; fill to row 71; INDEX in B8/B9; month-24 checks; plain 4.5 shown live (≈ $43,868) and fixed; zero-APY test; line chart (Months / Dollars, y from $0); tests a–d explained |
| 3 | Loan inputs + payment | 14 | 502 | 3:02 | B2 out-the-door price, B3 `=MIN(B2,Savings!B8)` (never retype), B4 financed, B5 contract rate vs APR, B6 term, B7 `=IF(B5=0,B4/B6,-PMT(B5/12,B6,B4))` and the minus sign, B8 total interest, B9 purchase + financing; 0% edge case; savings-exceed-price edge case; restore |
| 4 | Amortization schedule | 12 | 384 | 2:20 | Row 11 headers; row 12 cell by cell; month-1 check; row 13 links; the "opening points at B4" bug; fill to row 71; final ≈ $0; check block (SUM principal = B4, SUM interest = B8); interest-vs-principal chart |
| 5 | 60 vs 72, ownership, deliverables | 18 | 599 | 3:38 | Duplicate sheet → `Loan72`, B6 = 72, extend to row 83; `Compare` sheet scenario table linked to both sheets; difference row; **callout: smaller payment ≠ cheaper loan**; third lever + live 9% rehearsal; ownership block with fuel formula; monthly cash need; deliverables; sentence frame mapped to cells |
| 6 | Ready or Revise | 6 | 207 | 1:16 | Peer audit with specific fixes; math line; formula-structure test done live (Savings!B4 → 200 moves down payment and principal, then restored); research/explanation lines; one-line recap |
| | **Total** | **86** | **2,927** | **≈ 17:42** | |

If the ElevenLabs takes run slower than 2.9 words/s and the cut passes 18 minutes, the
cheapest trims are `rate-see`, `m1-endofmonth` → merge into `m1-check`, `amort-sums-see`,
`own-insurance` → merge into `own-fuel-inputs`, and `audit-explain`.

## Workbook the video builds

| Sheet | Cells | Contents |
|---|---|---|
| Savings | A1 | Title |
| | A2:B9 | Inputs and outputs exactly as §4 (B6 rate, B8/B9 INDEX outputs) |
| | A10:F71 | §5 schedule: headers row 10, month 0 row 11, month 1 row 12, filled to row 71 |
| | chart at H2 | Line chart, rows 11–35 (months 0–24): Closing balance and Total contributed; axes Months / Dollars; y min 0; title "Deposits do most of the work" |
| Loan | A2:B9 | §7 inputs and payment |
| | D2:F5 | Check block (not placed by the handout): F3 `=F71`, F4 `=SUM(E12:E71)`, F5 `=SUM(C12:C71)` |
| | A11:F71 | §8 amortization; headers row 11 |
| | chart at H2 | Interest and Principal per payment; axes Months / Dollars per payment; y min 0 |
| Loan72 | same as Loan | The §8 duplicate, B6 = 72, schedule extended to row 83, checks pointed at row 83 |
| Compare | A2:E6 | §9 scenario table: Base 60 (links to `Loan!B7:B9`), 72 months (links to `Loan72!B7:B9`), difference row (interest and total only), "one more lever" row |
| | A8:C18 | §10 ownership block: insurance 180, miles 600, mpg 30, $/gal 3.50, fuel `=B11/B12*B13`, maintenance 50, total `=SUM(B10,B14,B15)`, payment + ownership for 60 and 72 |

The video ends with every base input restored (Savings B2 500, B3 4.5%, B4 150; Loan B5 7%).

## Before you render — read this

1. **Run the whole script in one take.** Almost every check depends on cells built in earlier
   chapters. Exporting one chapter needs the earlier chapters fast-forwarded first (the
   driver's `fast=True` path).
2. **The 72-month copy is rebuilt, not copied.** The action vocabulary has no copy-sheet
   action, so scene `dup-sheet` narrates "Right click the tab → Move or Copy → Create a copy"
   while about 50 instant actions (mostly `set`) build `Loan72` (labels, formulas, fills, formats). Unlike a real
   copy, `Loan72` has no chart. If the driver gains a `copy_sheet` action, swap it in there.
3. **The "plain 4.5" trap is shown with `set`, not `type`.** In desktop Excel, typing 4.5 by
   hand into a cell *already* formatted as a percent is usually turned into 4.5% by
   "automatic percent entry". The trap mostly hits unformatted cells, pasted values and
   Google Sheets. That's why the narration says "Suppose B three holds a plain four point five"
   and doesn't say "type it". The check asserts ≈ $43,867.50 (§5 says "near $43,868").
4. **Teacher-only answers stay off screen.** Deck I slide 16's notes mark the tests a–c
   answers "do not project" (month 23; $4,189.41 at 2.0%; $4,928.38 at $175). The video
   explains how to run tests a–c but never runs them. The test-a highlight stops at row 20 so
   months 22–23 never appear. Test d (0% → $4,100) is published, so it is run live. For the
   same reason, the live Formula-structure demo in chapter 6 uses a **$200** deposit, not $175.
   Its values ($5,554.44 / $10,445.56) are derived, not printed anywhere.
5. **Payment difference is not on screen.** At full precision 199.43… − 231.63… = −$32.19,
   while Deck III prints "$32.20 less" (the difference of the rounded payments). The video says
   "about thirty two dollars" and the difference row only fills interest and total ($461.55 each).
6. **Out-the-door price:** §7 types 16000 in Loan!B2, but §1 says it should be a formula.
   The video types 16000 to match §7 and tells students to make their own a formula.
7. **Savings chart range is fixed at rows 11–35** (through month 24, as §5 asks). If a
   student changes B5, they have to re-range the chart. That's worth saying in class.
8. **Screen size:** a 13" MacBook Air at its default resolution can't show a 1000-pt-tall
   window. The driver clamps it and logs a note. Check that the zoom ranges still fit with a dryrun on that Mac.
9. **Text checks depend on formats** `$#,##0.00`, `0.00%` and `0.00000%`, plus column widths of 17
   (Savings/Loan B:F) and 20 (Compare C:E), so nothing shows `####`.
10. **Spoken vs caption text:** `say` is written for the voice ("B six", "A P Y"). Scenes whose
    captions differ carry a `caption` with cell names and acronyms written normally (B6, APY,
    Loan72, fueleconomy.gov).

## Every check the video asserts

105 checks. `±` checks compare the stored value; `text` checks compare what Excel displays.
**Bold** = a number printed in the handout's check boxes.

| # | Scene | Cell | Expects | Source |
|---|---|---|---|---|
| 1 | `initial` | `Savings!B2` | 500 ± 0.005 | §4 Savings inputs (B2 = 500) |
| 2 | `apy-type` | `Savings!B3` | 0.045 ± 1e-09 | §4 (B3 = 4.5%) · §3 “Enter 4.5% as 4.5% or 0.045” |
| 3 | `apy-type` | `Savings!B3` | text “4.50%” | §4 (B3 = 4.5%) · §3 “Enter 4.5% as 4.5% or 0.045” |
| 4 | `deposit` | `Savings!B4` | 150 ± 0.005 | §4 (B4 = 150) |
| 5 | `months` | `Savings!B5` | 24 ± 0 | §4 (B5 = 24) |
| 6 | `target` | `Savings!B7` | 4000 ± 0.005 | §4 (B7 = 4000) |
| 7 | `rate-root` | `Savings!B6` | 0.0036748094 ± 1e-09 | §3 worked conversion (r ≈ 0.0036748) |
| 8 | `rate-see` | `Savings!B6` | text “0.36748%” | §3 “about 0.367% per month” |
| 9 | `month0` | `Savings!E11` | 500 ± 0.005 | §5 row 11 (month 0) |
| 10 | `month0` | `Savings!F11` | 500 ± 0.005 | §5 row 11 (month 0) |
| 11 | `m1-month` | `Savings!B12` | 500 ± 0.005 | §5 row 12 |
| 12 | `m1-interest` | `Savings!C12` | 1.8374047 ± 1e-06 | §5 hand check “500 × 0.0036748 ≈ $1.84” |
| 13 | `m1-deposit` | `Savings!F12` | 650 ± 0.005 | §5 row 12 (F12 = F11 + D12) |
| 14 | `m1-check` | `Savings!E12` | 651.84 ± 0.005 | §5 printed check **Month 1 = $651.84** + hand check $1.84 |
| 15 | `m1-check` | `Savings!E12` | text “$651.84” | §5 printed check **Month 1 = $651.84** + hand check $1.84 |
| 16 | `m1-check` | `Savings!C12` | text “$1.84” | §5 printed check **Month 1 = $651.84** + hand check $1.84 |
| 17 | `m1-wrong` | `Savings!E12` | 651.875 ± 1e-06 | §5 trap line “$651.88? You used APY ÷ 12” |
| 18 | `m1-wrong` | `Savings!E12` | text “$651.88” | §5 trap line “$651.88? You used APY ÷ 12” |
| 19 | `m1-wrong-fix` | `Savings!E12` | 651.84 ± 0.005 | §5 Month 1 = $651.84 |
| 20 | `fill` | `Savings!A71` | 60 ± 0 | §5 “Copy row 12 through row 71 (month 60)” |
| 21 | `check-24` | `Savings!B8` | 4302.33 ± 0.005 | §5 printed checks **$4,302.33 / $202.33 / $4,100.00** |
| 22 | `check-24` | `Savings!B8` | text “$4,302.33” | §5 printed checks **$4,302.33 / $202.33 / $4,100.00** |
| 23 | `check-24` | `Savings!B9` | 202.33 ± 0.005 | §5 printed checks **$4,302.33 / $202.33 / $4,100.00** |
| 24 | `check-24` | `Savings!B9` | text “$202.33” | §5 printed checks **$4,302.33 / $202.33 / $4,100.00** |
| 25 | `check-24` | `Savings!F35` | 4100 ± 0.005 | §5 printed checks **$4,302.33 / $202.33 / $4,100.00** |
| 26 | `check-24` | `Savings!F35` | text “$4,100.00” | §5 printed checks **$4,302.33 / $202.33 / $4,100.00** |
| 27 | `trap-450` | `Savings!B8` | 43867.5 ± 0.01 | §5 trap line “near $43,868? You typed 4.5” |
| 28 | `trap-450-fix` | `Savings!B8` | 4302.33 ± 0.005 | §5 $4,302.33 |
| 29 | `zero-apy` | `Savings!B8` | 4100 ± 0.005 | §5 printed check **APY 0% → $4,100.00** · §6 test d |
| 30 | `zero-apy` | `Savings!B8` | text “$4,100.00” | §5 printed check **APY 0% → $4,100.00** · §6 test d |
| 31 | `zero-apy` | `Savings!B9` | 0 ± 0.005 | §5 printed check **APY 0% → $4,100.00** · §6 test d |
| 32 | `zero-restore` | `Savings!B8` | 4302.33 ± 0.005 | §5 $4,302.33 |
| 33 | `tests-bc` | `Savings!B8` | 4302.33 ± 0.005 | §6 “Restore the base inputs” |
| 34 | `loan-price` | `Loan!B2` | 16000 ± 0.005 | §7 B2 sample result $16,000.00 |
| 35 | `loan-price` | `Loan!B2` | text “$16,000.00” | §7 B2 sample result $16,000.00 |
| 36 | `down-payment` | `Loan!B3` | 4302.33 ± 0.005 | §7 B3 = $4,302.33 |
| 37 | `down-see` | `Loan!B3` | text “$4,302.33” | §7 B3 = $4,302.33 |
| 38 | `financed` | `Loan!B4` | 11697.67 ± 0.005 | §7 B4 = $11,697.67 |
| 39 | `financed` | `Loan!B4` | text “$11,697.67” | §7 B4 = $11,697.67 |
| 40 | `rate` | `Loan!B5` | 0.07 ± 1e-09 | §7 B5 = 7% |
| 41 | `term` | `Loan!B6` | 60 ± 0 | §7 B6 = 60 |
| 42 | `pmt-type` | `Loan!B7` | 231.63 ± 0.005 | §7 B7 = **$231.63** |
| 43 | `pmt-see` | `Loan!B7` | text “$231.63” | §7 B7 = $231.63 |
| 44 | `total-interest` | `Loan!B8` | 2200.0 ± 0.005 | §7 B8 = **$2,200.00** |
| 45 | `total-interest` | `Loan!B8` | text “$2,200.00” | §7 B8 = **$2,200.00** |
| 46 | `total-cost` | `Loan!B9` | 18200.0 ± 0.005 | §7 B9 = **$18,200.00** |
| 47 | `total-cost` | `Loan!B9` | text “$18,200.00” | §7 B9 = **$18,200.00** |
| 48 | `edge-zero` | `Loan!B7` | 194.96 ± 0.005 | §7 edge cases “B4 ÷ B6 (about $194.96) and interest is $0” |
| 49 | `edge-zero` | `Loan!B8` | 0 ± 0.005 | §7 edge cases “B4 ÷ B6 (about $194.96) and interest is $0” |
| 50 | `edge-cap` | `Loan!B3` | 16000 ± 0.005 | §7 edge cases “down payment is the full price and the amount financed is $0” |
| 51 | `edge-cap` | `Loan!B4` | 0 ± 0.005 | §7 edge cases “down payment is the full price and the amount financed is $0” |
| 52 | `edge-cap` | `Loan!B7` | 0 ± 0.005 | §7 edge cases “down payment is the full price and the amount financed is $0” |
| 53 | `edge-restore` | `Loan!B3` | 4302.33 ± 0.005 | §7 B3, B7 |
| 54 | `edge-restore` | `Loan!B7` | 231.63 ± 0.005 | §7 B3, B7 |
| 55 | `amort-row12b` | `Loan!F12` | 11534.28 ± 0.005 | Deck II slide 9 worked rows (month 1 closing $11,534.28) |
| 56 | `amort-check1` | `Loan!C12` | 68.24 ± 0.005 | §8 printed check **Month 1: interest $68.24, principal $163.39** |
| 57 | `amort-check1` | `Loan!C12` | text “$68.24” | §8 printed check **Month 1: interest $68.24, principal $163.39** |
| 58 | `amort-check1` | `Loan!E12` | 163.39 ± 0.005 | §8 printed check **Month 1: interest $68.24, principal $163.39** |
| 59 | `amort-check1` | `Loan!E12` | text “$163.39” | §8 printed check **Month 1: interest $68.24, principal $163.39** |
| 60 | `amort-row13` | `Loan!C13` | 67.28 ± 0.005 | Deck II slide 9 (month 2: $67.28, $11,369.93) |
| 61 | `amort-row13` | `Loan!F13` | 11369.93 ± 0.005 | Deck II slide 9 (month 2: $67.28, $11,369.93) |
| 62 | `amort-fill` | `Loan!A71` | 60 ± 0 | §8 “Copy row 13 down to month 60 (row 71)” |
| 63 | `amort-final` | `Loan!B71` | 230.28 ± 0.005 | §8 **Final closing ≈ $0.00** · Deck II slide 9 (month 60 opening $230.28) |
| 64 | `amort-final` | `Loan!F71` | 0 ± 0.005 | §8 **Final closing ≈ $0.00** · Deck II slide 9 (month 60 opening $230.28) |
| 65 | `amort-sums` | `Loan!F3` | 0 ± 0.005 | §8 **SUM(principal) = B4 · SUM(interest) = B8** |
| 66 | `amort-sums` | `Loan!F4` | 11697.67 ± 0.005 | §8 **SUM(principal) = B4 · SUM(interest) = B8** |
| 67 | `amort-sums` | `Loan!F5` | 2200.0 ± 0.005 | §8 **SUM(principal) = B4 · SUM(interest) = B8** |
| 68 | `amort-sums-see` | `Loan!F4` | text “$11,697.67” | §8 same |
| 69 | `amort-sums-see` | `Loan!F5` | text “$2,200.00” | §8 same |
| 70 | `dup-sheet` | `Loan72!B7` | 231.63 ± 0.005 | §8 (copy matches the 60-month sheet before B6 changes) |
| 71 | `dup-sheet` | `Loan72!F71` | 0 ± 0.005 | §8 (copy matches the 60-month sheet before B6 changes) |
| 72 | `dup-72` | `Loan72!A83` | 72 ± 0 | §8 “set B6 to 72 and extend to row 83” |
| 73 | `dup-72` | `Loan72!F3` | 0 ± 0.005 | §8 “set B6 to 72 and extend to row 83” |
| 74 | `dup-72-see` | `Loan72!B7` | 199.43 ± 0.005 | §9 sample check **72 months → $199.43, $2,661.55, $18,661.55** |
| 75 | `dup-72-see` | `Loan72!B7` | text “$199.43” | §9 sample check **72 months → $199.43, $2,661.55, $18,661.55** |
| 76 | `dup-72-see` | `Loan72!B8` | 2661.55 ± 0.005 | §9 sample check **72 months → $199.43, $2,661.55, $18,661.55** |
| 77 | `dup-72-see` | `Loan72!B8` | text “$2,661.55” | §9 sample check **72 months → $199.43, $2,661.55, $18,661.55** |
| 78 | `dup-72-see` | `Loan72!B9` | 18661.55 ± 0.005 | §9 sample check **72 months → $199.43, $2,661.55, $18,661.55** |
| 79 | `dup-72-see` | `Loan72!B9` | text “$18,661.55” | §9 sample check **72 months → $199.43, $2,661.55, $18,661.55** |
| 80 | `dup-72-see` | `Loan72!F4` | 11697.67 ± 0.005 | §9 sample check **72 months → $199.43, $2,661.55, $18,661.55** |
| 81 | `dup-72-see` | `Loan72!F5` | 2661.55 ± 0.005 | §9 sample check **72 months → $199.43, $2,661.55, $18,661.55** |
| 82 | `scenario-links` | `Compare!C3` | 231.63 ± 0.005 | §9 sample check **60 → $231.63, $2,200.00, $18,200.00; 72 → $199.43, $2,661.55, $18,661.55** |
| 83 | `scenario-links` | `Compare!D3` | 2200.0 ± 0.005 | §9 sample check **60 → $231.63, $2,200.00, $18,200.00; 72 → $199.43, $2,661.55, $18,661.55** |
| 84 | `scenario-links` | `Compare!E3` | 18200.0 ± 0.005 | §9 sample check **60 → $231.63, $2,200.00, $18,200.00; 72 → $199.43, $2,661.55, $18,661.55** |
| 85 | `scenario-links` | `Compare!C4` | 199.43 ± 0.005 | §9 sample check **60 → $231.63, $2,200.00, $18,200.00; 72 → $199.43, $2,661.55, $18,661.55** |
| 86 | `scenario-links` | `Compare!D4` | 2661.55 ± 0.005 | §9 sample check **60 → $231.63, $2,200.00, $18,200.00; 72 → $199.43, $2,661.55, $18,661.55** |
| 87 | `scenario-links` | `Compare!E4` | 18661.55 ± 0.005 | §9 sample check **60 → $231.63, $2,200.00, $18,200.00; 72 → $199.43, $2,661.55, $18,661.55** |
| 88 | `scenario-diff` | `Compare!D5` | 461.55 ± 0.005 | Deck III slide 3 ($461.55 more) |
| 89 | `scenario-diff` | `Compare!D5` | text “$461.55” | Deck III slide 3 ($461.55 more) |
| 90 | `scenario-diff` | `Compare!E5` | 461.55 ± 0.005 | Deck III slide 3 ($461.55 more) |
| 91 | `live-change` | `Compare!C3` | 242.82 ± 0.005 | Deck III slide 4 “Higher rate 9%: $242.82, $2,871.79” |
| 92 | `live-change` | `Compare!D3` | 2871.79 ± 0.005 | Deck III slide 4 “Higher rate 9%: $242.82, $2,871.79” |
| 93 | `own-intro` | `Compare!C3` | 231.63 ± 0.005 | §9 base payment restored |
| 94 | `own-insurance` | `Compare!B10` | 180 ± 0.005 | Deck III slide 7 sample ($180) |
| 95 | `own-fuel` | `Compare!B14` | 70 ± 0.005 | §10 fuel formula · Deck III slide 7 (600 ÷ 30 × $3.50 = $70) |
| 96 | `own-fuel` | `Compare!B14` | text “$70.00” | §10 fuel formula · Deck III slide 7 (600 ÷ 30 × $3.50 = $70) |
| 97 | `own-total` | `Compare!B16` | 300 ± 0.005 | Deck III slide 7 ($300/month) |
| 98 | `own-need` | `Compare!B17` | 531.63 ± 0.005 | Deck III slide 7 ($531.63 / $499.43) |
| 99 | `own-need` | `Compare!B18` | 499.43 ± 0.005 | Deck III slide 7 ($531.63 / $499.43) |
| 100 | `audit-structure` | `Savings!B8` | 5554.44 ± 0.005 | Ready/Revise “Formula structure” line — **derived** (not printed): deposit $200 → $5,554.44 |
| 101 | `audit-structure` | `Loan!B3` | 5554.44 ± 0.005 | Ready/Revise “Formula structure” line — **derived** (not printed): deposit $200 → $5,554.44 |
| 102 | `audit-structure` | `Loan!B4` | 10445.56 ± 0.005 | Ready/Revise “Formula structure” line — **derived** (not printed): deposit $200 → $5,554.44 |
| 103 | `audit-structure-2` | `Savings!B8` | 4302.33 ± 0.005 | Base restored: §5 $4,302.33, §7 $11,697.67 / $231.63 |
| 104 | `audit-structure-2` | `Loan!B4` | 11697.67 ± 0.005 | Base restored: §5 $4,302.33, §7 $11,697.67 / $231.63 |
| 105 | `audit-structure-2` | `Loan!B7` | 231.63 ± 0.005 | Base restored: §5 $4,302.33, §7 $11,697.67 / $231.63 |
