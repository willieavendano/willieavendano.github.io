#!/usr/bin/env python3
"""Practice and exemplar workbooks for the Computer Science Math kits.

Two workbook families:

  csm-p<N>-*-practice.xlsx   guided drills — the "practice" beat of a kit
  csm-<id>-exemplars.xlsx    the SAME task built four times, one tab per
                             rubric level, plus a "What Changed" tab naming
                             the specific difference between each pair

Run from the repo root:

    python3 tools/make-csmath-kits.py

Idempotent: re-running overwrites the targets with identical content.
Requires openpyxl.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from importlib import import_module

_mw = import_module("make-workbooks".replace("-", "_")) if False else None

# ── shared style constants (kept in sync with tools/make-workbooks.py) ──
CUSHMAN_BLUE = "0E406A"
BRIGHT = "0071CE"
PAPER_DEEP = "F3EFE7"
INK_SOFT = "55504A"
GOOD = "2C6E49"
WARN = "8A5A0B"
BAD = "A33A2A"

HEADER_FILL = PatternFill("solid", fgColor=CUSHMAN_BLUE)
HEADER_FONT = Font(bold=True, color="FFFFFF")
BAND_FILL = PatternFill("solid", fgColor=PAPER_DEEP)
TITLE_FONT = Font(bold=True, color=CUSHMAN_BLUE, size=16)
H2_FONT = Font(bold=True, color=CUSHMAN_BLUE, size=12)
BOLD = Font(bold=True)
NOTE_FONT = Font(italic=True, color=INK_SOFT)
WRAP = Alignment(wrap_text=True, vertical="top")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "computer-science-math", "resources")


def set_widths(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def header_row(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def title_block(ws, title, subtitle=None):
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    r = 2
    if subtitle:
        ws["A2"] = subtitle
        ws["A2"].font = NOTE_FONT
        ws["A2"].alignment = WRAP
        r = 3
    return r + 1


def read_me(wb, title, lines, first=True):
    ws = wb.active if first else wb.create_sheet()
    ws.title = "READ ME FIRST"
    set_widths(ws, [30, 96])
    r = title_block(ws, title)
    for label, body in lines:
        ws.cell(row=r, column=1, value=label).font = BOLD
        c = ws.cell(row=r, column=2, value=body)
        c.alignment = WRAP
        ws.row_dimensions[r].height = max(15, 13 * (1 + len(body) // 92))
        r += 1
    return ws


# ═══════════════════════════════════════════════════════════════════
# Cornerstone II practice — HYSA first, then the loan
# ═══════════════════════════════════════════════════════════════════

def build_p2_interest_practice():
    wb = Workbook()
    read_me(wb, "Cornerstone II Practice — Interest, Both Directions", [
        ("What this is",
         "Five drills. Do them in order — each one sets up the next. Nothing here is graded; this is where you "
         "make your mistakes cheaply, before the cornerstone counts."),
        ("Why savings first",
         "Compound interest is one machine. Pointed at your savings it makes you money; pointed at a loan it "
         "costs you money. Same formula, opposite sign. Meet it as a friend first — the amortisation table "
         "stops being frightening once you have already built the growth curve."),
        ("The one rule",
         "Every number that could be computed MUST be computed. If you type a result into a cell, you have "
         "drawn a picture of a model instead of building one. Change an input; if nothing moves, it is broken."),
        ("When you are done",
         "You should be able to answer: why does a longer loan with a smaller monthly payment cost more?"),
    ])

    # ── Drill 1 & 2: HYSA growth ──
    ws = wb.create_sheet("1-2 HYSA Growth")
    set_widths(ws, [26, 15, 15, 15, 15, 46])
    r = title_block(ws, "Drills 1 & 2 — Interest working FOR you",
                    "A high-yield savings account. Build the growth table, then change the compounding.")
    ws.cell(row=r, column=1, value="INPUTS — change these, everything else must follow").font = H2_FONT
    r += 1
    inputs = [("Starting balance", 500, "$#,##0.00"),
              ("Annual rate (APY)", 0.045, "0.00%"),
              ("Compounds per year", 12, "0"),
              ("Years", 5, "0")]
    first_input = r
    for name, val, fmt in inputs:
        ws.cell(row=r, column=1, value=name).font = BOLD
        c = ws.cell(row=r, column=2, value=val)
        c.number_format = fmt
        c.fill = BAND_FILL
        r += 1
    B_START, B_RATE, B_N, B_YEARS = (f"$B${first_input + i}" for i in range(4))

    r += 1
    ws.cell(row=r, column=1, value="Period").font = HEADER_FONT
    ws.cell(row=r, column=2, value="Balance start").font = HEADER_FONT
    ws.cell(row=r, column=3, value="Interest earned").font = HEADER_FONT
    ws.cell(row=r, column=4, value="Balance end").font = HEADER_FONT
    header_row(ws, r, 4)
    tbl = r + 1
    for i in range(60):
        row = tbl + i
        ws.cell(row=row, column=1, value=i + 1)
        ws.cell(row=row, column=2,
                value=f"={B_START}" if i == 0 else f"=D{row-1}").number_format = "$#,##0.00"
        ws.cell(row=row, column=3, value=f"=B{row}*{B_RATE}/{B_N}").number_format = "$#,##0.00"
        ws.cell(row=row, column=4, value=f"=B{row}+C{row}").number_format = "$#,##0.00"
    ws.cell(row=tbl - 1, column=6,
            value="Drill 1: this table is built for you — read every formula and say out loud what it does.").alignment = WRAP
    ws.cell(row=tbl + 1, column=6,
            value="Drill 2: change 'Compounds per year' from 12 to 365. Write one sentence below explaining "
                  "why the ending balance barely moves.").alignment = WRAP
    ws.cell(row=tbl + 4, column=6, value="Your sentence:").font = BOLD
    ws.cell(row=tbl + 5, column=6, value="").fill = BAND_FILL

    chart = LineChart()
    chart.title = "Savings growth"
    chart.y_axis.title = "Balance"
    chart.x_axis.title = "Month"
    chart.height, chart.width = 7, 14
    chart.add_data(Reference(ws, min_col=4, min_row=tbl - 1, max_row=tbl + 59), titles_from_data=True)
    ws.add_chart(chart, f"H{tbl + 8}")

    # ── Drill 3 & 4: the loan ──
    ws = wb.create_sheet("3-4 The Loan")
    set_widths(ws, [26, 15, 15, 15, 15, 46])
    r = title_block(ws, "Drills 3 & 4 — The same machine, pointed at you",
                    "Now you are the one paying. Build the payment, then split it.")
    ws.cell(row=r, column=1, value="INPUTS").font = H2_FONT
    r += 1
    loan_inputs = [("Amount financed", 12000, "$#,##0.00"),
                   ("Annual rate (APR)", 0.07, "0.00%"),
                   ("Term (months)", 60, "0")]
    fi = r
    for name, val, fmt in loan_inputs:
        ws.cell(row=r, column=1, value=name).font = BOLD
        c = ws.cell(row=r, column=2, value=val)
        c.number_format = fmt
        c.fill = BAND_FILL
        r += 1
    L_AMT, L_APR, L_TERM = (f"$B${fi + i}" for i in range(3))

    ws.cell(row=r, column=1, value="Monthly payment").font = BOLD
    ws.cell(row=r, column=2, value=f"=PMT({L_APR}/12,{L_TERM},-{L_AMT})").number_format = "$#,##0.00"
    ws.cell(row=r, column=6,
            value="Drill 3: PMT does the work. Look it up — what do the three arguments mean? "
                  "Why is the amount negative?").alignment = WRAP
    pay = f"$B${r}"
    r += 2

    for i, h in enumerate(["Month", "Payment", "Interest", "Principal", "Balance"], start=1):
        ws.cell(row=r, column=i, value=h)
    header_row(ws, r, 5)
    tbl = r + 1
    for i in range(60):
        row = tbl + i
        ws.cell(row=row, column=1, value=i + 1)
        ws.cell(row=row, column=2, value=f"={pay}").number_format = "$#,##0.00"
        prev_bal = L_AMT if i == 0 else f"E{row-1}"
        ws.cell(row=row, column=3, value=f"={prev_bal}*{L_APR}/12").number_format = "$#,##0.00"
        ws.cell(row=row, column=4, value=f"=B{row}-C{row}").number_format = "$#,##0.00"
        ws.cell(row=row, column=5, value=f"={prev_bal}-D{row}").number_format = "$#,##0.00"
    ws.cell(row=tbl + 2, column=7,
            value="Drill 4: chart Interest and Principal together. Find the month they cross. "
                  "Explain what the crossover means for someone paying this loan.").alignment = WRAP

    chart = LineChart()
    chart.title = "Interest vs principal"
    chart.y_axis.title = "Dollars"
    chart.x_axis.title = "Month"
    chart.height, chart.width = 7, 14
    chart.add_data(Reference(ws, min_col=3, max_col=4, min_row=tbl - 1, max_row=tbl + 59), titles_from_data=True)
    ws.add_chart(chart, f"G{tbl + 6}")

    # ── Drill 5: the comparison ──
    ws = wb.create_sheet("5 Which Loan")
    set_widths(ws, [30, 18, 18, 18, 52])
    r = title_block(ws, "Drill 5 — The trap",
                    "A smaller monthly payment is not a cheaper loan. Prove it.")
    for i, h in enumerate(["Term", "Monthly payment", "Total paid", "Total interest"], start=1):
        ws.cell(row=r, column=i, value=h)
    header_row(ws, r, 4)
    r += 1
    for term in (36, 48, 60, 72, 84):
        ws.cell(row=r, column=1, value=f"{term} months")
        ws.cell(row=r, column=2, value=f"=PMT($B$20/12,{term},-$B$19)").number_format = "$#,##0.00"
        ws.cell(row=r, column=3, value=f"=B{r}*{term}").number_format = "$#,##0.00"
        ws.cell(row=r, column=4, value=f"=C{r}-$B$19").number_format = "$#,##0.00"
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="Amount financed").font = BOLD
    ws.cell(row=r, column=2, value=12000).number_format = "$#,##0.00"
    ws.cell(row=r, column=2).fill = BAND_FILL
    ws.cell(row=r + 1, column=1, value="Annual rate (APR)").font = BOLD
    ws.cell(row=r + 1, column=2, value=0.07).number_format = "0.00%"
    ws.cell(row=r + 1, column=2).fill = BAND_FILL
    ws.cell(row=r + 3, column=1,
            value="The inputs live in B19 and B20 — the formulas above point at them. "
                  "Change the rate and watch every row move.").alignment = WRAP
    ws.cell(row=r + 5, column=1, value="Which term would you take, and why? (One paragraph.)").font = BOLD

    path = os.path.join(RES, "csm-p2-interest-practice.xlsx")
    wb.save(path)
    return path


# ═══════════════════════════════════════════════════════════════════
# Exemplars — the same task, built four ways
# ═══════════════════════════════════════════════════════════════════

EXEMPLAR_TASK_U2 = "Model a $12,000 car loan at 7% APR over 60 months. Report the monthly payment and the total interest paid."

def _ex_header(ws, level, name, gloss, task):
    colour = {4: GOOD, 3: GOOD, 2: WARN, 1: BAD}[level]
    ws["A1"] = f"LEVEL {level} — {name}"
    ws["A1"].font = Font(bold=True, size=15, color=colour)
    ws["A2"] = gloss
    ws["A2"].font = NOTE_FONT
    ws["A3"] = f"Task: {task}"
    ws["A3"].font = NOTE_FONT
    ws["A3"].alignment = WRAP
    return 5


def build_u2_exemplars():
    wb = Workbook()
    read_me(wb, "Cornerstone II — What Each Level Looks Like", [
        ("What this is",
         "The same car-loan task, built four times. Level 4 is what excellence looks like; Level 1 is what "
         "gets handed in when someone runs out of time. Open them side by side."),
        ("How to use it",
         "Read this BEFORE you start building, not after you are graded. Then open 'What Changed' — it names "
         "the exact difference between each pair of levels."),
        ("The fastest way to lose points",
         "Typing in a number that should have been computed. Every level below 3 fails on that alone, no "
         "matter how good it looks."),
        ("Task", EXEMPLAR_TASK_U2),
    ])

    LEVELS = [
        (4, "Advanced", "Publishable. Someone else could pick this up and use it."),
        (3, "Proficient", "Works and is honest. The expected standard."),
        (2, "Developing", "Partly works, or works for the wrong reasons."),
        (1, "Beginning", "Incomplete, or the numbers cannot be trusted."),
    ]

    for level, name, gloss in LEVELS:
        ws = wb.create_sheet(f"Level {level} — {name}")
        set_widths(ws, [28, 16, 15, 15, 15, 50])
        r = _ex_header(ws, level, name, gloss, EXEMPLAR_TASK_U2)

        if level == 4:
            ws.cell(row=r, column=1, value="INPUTS  (change any of these — everything follows)").font = H2_FONT
            r += 1
            base = r
            for nm, val, fmt in [("Vehicle price", 15000, "$#,##0.00"),
                                 ("Down payment", 3000, "$#,##0.00"),
                                 ("Annual rate (APR)", 0.07, "0.00%"),
                                 ("Term (months)", 60, "0")]:
                ws.cell(row=r, column=1, value=nm).font = BOLD
                c = ws.cell(row=r, column=2, value=val); c.number_format = fmt; c.fill = BAND_FILL
                r += 1
            ws.cell(row=r, column=1, value="Amount financed").font = BOLD
            ws.cell(row=r, column=2, value=f"=B{base}-B{base+1}").number_format = "$#,##0.00"
            fin = r; r += 2
            ws.cell(row=r, column=1, value="OUTPUTS").font = H2_FONT
            r += 1
            ws.cell(row=r, column=1, value="Monthly payment").font = BOLD
            ws.cell(row=r, column=2, value=f"=IF(B{base+3}<=0,\"check term\",PMT(B{base+2}/12,B{base+3},-B{fin}))").number_format = "$#,##0.00"
            pay = f"$B${r}"; r += 1
            ws.cell(row=r, column=1, value="Total paid").font = BOLD
            ws.cell(row=r, column=2, value=f"={pay}*B{base+3}").number_format = "$#,##0.00"
            r += 1
            ws.cell(row=r, column=1, value="Total interest").font = BOLD
            ws.cell(row=r, column=2, value=f"=B{r-1}-B{fin}").number_format = "$#,##0.00"
            r += 2
            ws.cell(row=r, column=6, value="Note the IF(): a zero or negative term would produce a nonsense "
                                           "payment, so the model refuses instead of lying.").alignment = WRAP
            for i, h in enumerate(["Month", "Payment", "Interest", "Principal", "Balance"], start=1):
                ws.cell(row=r, column=i, value=h)
            header_row(ws, r, 5)
            t = r + 1
            for i in range(60):
                row = t + i
                ws.cell(row=row, column=1, value=i + 1)
                ws.cell(row=row, column=2, value=f"={pay}").number_format = "$#,##0.00"
                prev = f"$B${fin}" if i == 0 else f"E{row-1}"
                ws.cell(row=row, column=3, value=f"={prev}*$B${base+2}/12").number_format = "$#,##0.00"
                ws.cell(row=row, column=4, value=f"=B{row}-C{row}").number_format = "$#,##0.00"
                ws.cell(row=row, column=5, value=f"={prev}-D{row}").number_format = "$#,##0.00"
            ch = LineChart(); ch.title = "Interest vs principal over the life of the loan"
            ch.y_axis.title = "Dollars"; ch.x_axis.title = "Month"; ch.height, ch.width = 7, 15
            ch.add_data(Reference(ws, min_col=3, max_col=4, min_row=r, max_row=t + 59), titles_from_data=True)
            ws.add_chart(ch, f"G{t}")

        elif level == 3:
            ws.cell(row=r, column=1, value="Inputs").font = H2_FONT
            r += 1
            base = r
            for nm, val, fmt in [("Amount financed", 12000, "$#,##0.00"),
                                 ("APR", 0.07, "0.00%"),
                                 ("Term (months)", 60, "0")]:
                ws.cell(row=r, column=1, value=nm).font = BOLD
                c = ws.cell(row=r, column=2, value=val); c.number_format = fmt; c.fill = BAND_FILL
                r += 1
            ws.cell(row=r, column=1, value="Monthly payment").font = BOLD
            ws.cell(row=r, column=2, value=f"=PMT(B{base+1}/12,B{base+2},-B{base})").number_format = "$#,##0.00"
            pay = f"$B${r}"; r += 1
            ws.cell(row=r, column=1, value="Total interest").font = BOLD
            ws.cell(row=r, column=2, value=f"={pay}*B{base+2}-B{base}").number_format = "$#,##0.00"
            r += 2
            for i, h in enumerate(["Month", "Payment", "Interest", "Principal", "Balance"], start=1):
                ws.cell(row=r, column=i, value=h)
            header_row(ws, r, 5)
            t = r + 1
            for i in range(60):
                row = t + i
                ws.cell(row=row, column=1, value=i + 1)
                ws.cell(row=row, column=2, value=f"={pay}").number_format = "$#,##0.00"
                prev = f"$B${base}" if i == 0 else f"E{row-1}"
                ws.cell(row=row, column=3, value=f"={prev}*$B${base+1}/12").number_format = "$#,##0.00"
                ws.cell(row=row, column=4, value=f"=B{row}-C{row}").number_format = "$#,##0.00"
                ws.cell(row=row, column=5, value=f"={prev}-D{row}").number_format = "$#,##0.00"
            ch = LineChart(); ch.title = "Interest vs principal"
            ch.height, ch.width = 6, 13
            ch.add_data(Reference(ws, min_col=3, max_col=4, min_row=r, max_row=t + 59), titles_from_data=True)
            ws.add_chart(ch, f"G{t}")
            ws.cell(row=t + 62, column=1,
                    value="Missing vs Level 4: no down-payment input, no edge-case guard, "
                          "axes unlabelled.").alignment = WRAP

        elif level == 2:
            ws.cell(row=r, column=1, value="Car loan").font = H2_FONT
            r += 1
            ws.cell(row=r, column=1, value="Amount"); ws.cell(row=r, column=2, value=12000).number_format = "$#,##0.00"
            r += 1
            ws.cell(row=r, column=1, value="Payment")
            ws.cell(row=r, column=2, value="=PMT(0.07/12,60,-12000)").number_format = "$#,##0.00"
            ws.cell(row=r, column=6, value="⚠ Rate and term are buried INSIDE the formula. Changing the "
                                           "input cell above does nothing.").alignment = WRAP
            ws.cell(row=r, column=6).font = Font(color=WARN)
            pay_row = r
            r += 1
            ws.cell(row=r, column=1, value="Total interest")
            ws.cell(row=r, column=2, value=2256.86).number_format = "$#,##0.00"
            ws.cell(row=r, column=6, value="⚠ Typed in from a calculator. It is correct RIGHT NOW — which is "
                                           "what makes it dangerous. Change the rate and it silently lies.").alignment = WRAP
            ws.cell(row=r, column=6).font = Font(color=WARN)
            r += 2
            for i, h in enumerate(["Month", "Interest", "Principal", "Balance"], start=1):
                ws.cell(row=r, column=i, value=h)
            header_row(ws, r, 4)
            t = r + 1
            for i in range(12):
                row = t + i
                ws.cell(row=row, column=1, value=i + 1)
                prev = "12000" if i == 0 else f"D{row-1}"
                ws.cell(row=row, column=2, value=f"={prev}*0.07/12").number_format = "$#,##0.00"
                ws.cell(row=row, column=3, value=f"=$B${pay_row}-B{row}").number_format = "$#,##0.00"
                ws.cell(row=row, column=4, value=f"={prev}-C{row}").number_format = "$#,##0.00"
            ws.cell(row=t + 13, column=1,
                    value="⚠ Only 12 of 60 months built — the schedule stops before the answer.").alignment = WRAP
            ws.cell(row=t + 13, column=1).font = Font(color=WARN)

        else:
            ws.cell(row=r, column=1, value="car loan stuff").font = H2_FONT
            r += 2
            ws.cell(row=r, column=1, value="monthly payment")
            ws.cell(row=r, column=2, value=237.6).number_format = "$#,##0.00"
            r += 1
            ws.cell(row=r, column=1, value="total")
            ws.cell(row=r, column=2, value=14256)
            r += 1
            ws.cell(row=r, column=1, value="interest")
            ws.cell(row=r, column=2, value=2256)
            r += 2
            for msg in [
                "✕ Every number is typed. There is not one formula in this sheet.",
                "✕ Nothing states the rate or the term, so the answer cannot be checked.",
                "✕ No amortisation schedule, no chart, no conclusion.",
                "✕ Change any assumption and this sheet says exactly the same thing — which is how you know "
                "it is not a model.",
            ]:
                c = ws.cell(row=r, column=1, value=msg)
                c.font = Font(color=BAD)
                c.alignment = WRAP
                r += 1

    # ── What Changed ──
    ws = wb.create_sheet("What Changed")
    set_widths(ws, [16, 52, 52])
    r = title_block(ws, "What Changed Between Levels",
                    "The specific difference — not a vibe. Each row is one concrete move up.")
    for i, h in enumerate(["Step", "What was wrong below", "What fixes it"], start=1):
        ws.cell(row=r, column=i, value=h)
    header_row(ws, r, 3)
    r += 1
    steps = [
        ("1 → 2",
         "Every number typed in by hand; no formulas at all. The sheet cannot be checked or reused.",
         "Compute at least the payment with a real formula (PMT) and start an amortisation schedule."),
        ("2 → 3",
         "Rate and term buried inside formulas; total interest typed from a calculator; schedule stops at "
         "month 12.",
         "Lift every assumption into its own labelled input cell, point the formulas at those cells, and "
         "build all 60 months so the schedule actually reaches zero."),
        ("3 → 4",
         "Works, but only models the amount financed — no vehicle price or down payment, no protection "
         "against nonsense inputs, chart axes unlabelled.",
         "Add price and down payment as inputs with amount financed derived from them; guard the edge case "
         "with IF(); label both axes and title the chart with the question it answers."),
    ]
    for step, wrong, fix in steps:
        ws.cell(row=r, column=1, value=step).font = BOLD
        ws.cell(row=r, column=2, value=wrong).alignment = WRAP
        ws.cell(row=r, column=3, value=fix).alignment = WRAP
        ws.row_dimensions[r].height = 46
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="The test").font = BOLD
    ws.cell(row=r, column=2,
            value="Change one input. If the answer does not move, you are at Level 1 no matter how it looks.").alignment = WRAP

    path = os.path.join(RES, "csm-u2-exemplars.xlsx")
    wb.save(path)
    return path


def main():
    os.makedirs(RES, exist_ok=True)
    for fn in (build_p2_interest_practice, build_u2_exemplars):
        p = fn()
        print(f"wrote {os.path.relpath(p, ROOT)}")


if __name__ == "__main__":
    main()
