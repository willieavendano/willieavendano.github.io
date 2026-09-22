#!/usr/bin/env python3
"""Regenerable Excel workbook builders for course resources.

Run directly to (re)write every workbook this script knows how to build.
Idempotent: re-running overwrites the target file(s) with the same content.

    python3 tools/make-workbooks.py

Requires openpyxl (pip3 install --user openpyxl).
"""

from __future__ import annotations

import os
from datetime import date, timedelta

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

# ---------------------------------------------------------------------------
# Shared style constants (matches assets/css/site.css --blue / --paper-deep)
# ---------------------------------------------------------------------------

CUSHMAN_BLUE = "0E406A"
PAPER_DEEP = "F3EFE7"
INK = "141412"
INK_SOFT = "55504A"

HEADER_FILL = PatternFill("solid", fgColor=CUSHMAN_BLUE)
HEADER_FONT = Font(bold=True, color="FFFFFF")
BAND_FILL = PatternFill("solid", fgColor=PAPER_DEEP)
SECTION_FILL = PatternFill("solid", fgColor=CUSHMAN_BLUE)
SECTION_FONT = Font(bold=True, color="FFFFFF", size=12)
TITLE_FONT = Font(bold=True, color=CUSHMAN_BLUE, size=16)
BOLD = Font(bold=True, color=INK)
NOTE_FONT = Font(italic=True, color=INK_SOFT)
THIN = Side(style="thin", color="CCCCCC")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def style_header_row(ws, row, num_cols):
    for col in range(1, num_cols + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def set_widths(ws, widths):
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width


# ---------------------------------------------------------------------------
# CS Math: Cornerstone I starter workbook
# ---------------------------------------------------------------------------

# Data-source color key (light tints so black text stays readable). These hex
# values are the single source of truth for both the static fills and the
# conditional-formatting rules.
MACRO_SOURCES = [
    # Source, What it's good for, Where to get it, Color hex
    (
        "MyFitnessPal",
        "App database; convenient, user-submitted values",
        "myfitnesspal.com (or any food-logging app)",
        "D9E8F5",
    ),
    (
        "USDA FoodData Central",
        "Government reference; best for whole foods and basic ingredients",
        "fdc.nal.usda.gov (downloadable datasets)",
        "DDEBD3",
    ),
    (
        "Open Food Facts",
        "Open, crowd-sourced; best for packaged and branded foods",
        "world.openfoodfacts.org (CSV export)",
        "FBE7C6",
    ),
    (
        "Manufacturer label",
        "The package itself; authoritative for that exact product",
        "the label on the product",
        "E7DDF2",
    ),
    (
        "Restaurant nutrition",
        "Published by the restaurant; portions still vary",
        "the restaurant's site or app",
        "F7D6D0",
    ),
    (
        "Estimate / other",
        "Your own call; flag it honestly",
        "\u2014",
        "E8E8E4",
    ),
]

SOURCE_FILLS = {
    name: PatternFill("solid", fgColor=hex_code)
    for name, _good, _where, hex_code in MACRO_SOURCES
}
SOURCE_HEX = {name: hex_code for name, _good, _where, hex_code in MACRO_SOURCES}

FOOD_TABLE_ROWS = [
    # Food, Serving, Calories, Protein (g), Carbs (g), Fat (g), Source
    ("Egg, large", "1 egg", 72, 6.3, 0.4, 4.8, "USDA FoodData Central"),
    ("White rice, cooked", "1 cup", 205, 4.3, 44.5, 0.4, "USDA FoodData Central"),
    ("Chicken breast, grilled", "100 g", 165, 31.0, 0, 3.6, "USDA FoodData Central"),
    ("Black beans, cooked", "1 cup", 227, 15.2, 40.8, 0.9, "USDA FoodData Central"),
    (
        "Cafecito con azucar (Cuban coffee, sweet)",
        "1 cup (8 oz)",
        40,
        0.5,
        8.0,
        1.0,
        "MyFitnessPal",
    ),
    ("Plantain, fried (maduros)", "1 cup", 250, 1.4, 47.0, 8.6, "Restaurant nutrition"),
    ("Ropa vieja (shredded beef)", "1 cup", 285, 26.0, 8.0, 17.0, "Restaurant nutrition"),
    ("Yuca con mojo", "1 cup", 220, 1.6, 52.0, 0.3, "Restaurant nutrition"),
    ("Avocado", "1/2 fruit", 160, 2.0, 8.5, 14.7, "USDA FoodData Central"),
    ("Croqueta (ham)", "1 piece", 130, 4.0, 10.0, 8.0, "Open Food Facts"),
    ("Whole wheat bread", "1 slice", 81, 4.0, 13.8, 1.1, "Manufacturer label"),
    ("Greek yogurt, plain", "1 cup (170 g)", 100, 17.0, 6.0, 0.7, "Open Food Facts"),
    ("Banana", "1 medium", 105, 1.3, 27.0, 0.4, "USDA FoodData Central"),
    ("Pizza slice, cheese", "1 slice", 285, 12.2, 35.7, 10.4, "Restaurant nutrition"),
    ("Cafe con leche", "1 cup (8 oz)", 110, 5.0, 11.0, 5.0, "Estimate / other"),
]

FOOD_TABLE_HEADER_ROW = 1
FOOD_TABLE_FIRST_DATA_ROW = 2
FOOD_TABLE_LAST_DATA_ROW = FOOD_TABLE_FIRST_DATA_ROW + len(FOOD_TABLE_ROWS) - 1  # 16
FOOD_TABLE_LAST_ROW = 100  # dropdown / formatting coverage for foods students add

FOOD_TABLE_HEADERS = [
    "Food", "Serving", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)", "Source",
]

DAILY_LOG_HEADERS = [
    "Date", "Meal", "Food", "Servings", "Source",
    "Calories", "Protein (g)", "Carbs (g)", "Fat (g)",
]
DAILY_LOG_EXAMPLES = [
    # Date, Meal, Food, Servings -- Source + macros intentionally left blank
    ("2026-09-21", "Breakfast", "Egg, large", 2),
    ("2026-09-21", "Lunch", "White rice, cooked", 1),
    ("2026-09-21", "Dinner", "Ropa vieja (shredded beef)", 1.5),
]
DAILY_LOG_VALIDATION_ROWS = 200  # ~200 rows of dropdown coverage, per brief

MEAL_OPTIONS = ["Breakfast", "Lunch", "Dinner", "Snacks"]

WEEKLY_SUMMARY_START = date(2026, 9, 21)
WEEKLY_SUMMARY_DAYS = 14


def _source_dropdown_formula():
    last = len(MACRO_SOURCES) + 1  # data rows 2..len+1
    return f"='Sources'!$A$2:$A${last}"


def _food_dropdown_formula():
    return f"='Food Table'!$A${FOOD_TABLE_FIRST_DATA_ROW}:$A${FOOD_TABLE_LAST_ROW}"


def build_read_me_sheet(wb):
    ws = wb.active
    ws.title = "READ ME FIRST"
    set_widths(ws, [26, 90])

    ws["A1"] = "Cornerstone I -- Food & Macro Tracker"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:B1")

    rows = [
        (
            "What is a cornerstone?",
            "Every unit in this course ends with a cornerstone project: a working model "
            "you design and build yourself, then present to the class. This workbook is "
            "the starter file for Cornerstone I -- it is NOT the finished project. It's "
            "the frame you build the real thing inside.",
        ),
        (
            "What's already built for you",
            "The Sources tab (reference table + color key). The Food Table headers and "
            "15 starter foods with real, approximate macro values and a Source for each "
            "(add your own -- aim for 25+ by presentation day). The Daily Log headers, "
            "with dropdowns in the Meal, Food, and Source columns. The Weekly Summary "
            "and Dashboard layouts, with labeled boxes waiting for your formulas.",
        ),
        (
            "Source every number",
            "Every macro value you log must have a data origin, and you must record it in "
            "the Source column. The Sources tab lists the six accepted sources and the "
            "color that goes with each. Color-code every food's Source cell -- the color "
            "tells the reader how much to trust the number. A label beats an estimate.",
        ),
        (
            "What you build",
            "1) Grow the Food Table with foods you actually eat, each with its Source. "
            "2) In the Daily Log, write VLOOKUP formulas that pull each row's Source and "
            "macros from the Food Table and multiply the macros by Servings. 3) In the "
            "Weekly Summary, write SUMIF/AVERAGEIF formulas that roll your log up by "
            "date. 4) In the Dashboard, summarize those daily figures and build at least "
            "one honest chart (no answer charts are pre-built for you).",
        ),
        (
            "Log 14 days",
            "The cornerstone requires at least 14 days of your own logged food data. "
            "Start early -- you cannot cram two weeks of real eating in the last night.",
        ),
        (
            "Two deliverables",
            "1) The final spreadsheet (this workbook, completed). 2) A final "
            "presentation to the class: a working tracker plus one real insight about "
            "your own eating patterns -- not just charts, an actual observation.",
        ),
        (
            "No answers here",
            "There are no formulas hidden anywhere in this workbook. Every formula you "
            "see in your finished tracker will be one you wrote. If a cell looks empty, "
            "that's on purpose -- that's your work.",
        ),
        (
            "Presentation date",
            "Thursday, October 15 (Week 8 of the Year Calendar). Bring a working tracker "
            "and the insight you found in your own data.",
        ),
        (
            "Rubric",
            "On the course kit page for this cornerstone (the same page linked from the "
            "class site) -- open the page and read it before you start building.",
        ),
    ]

    r = 3
    for heading, body in rows:
        ws.cell(row=r, column=1, value=heading).font = BOLD
        ws.cell(row=r, column=1).alignment = Alignment(vertical="top", wrap_text=True)
        body_cell = ws.cell(row=r, column=2, value=body)
        body_cell.alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[r].height = 60
        r += 1

    ws.freeze_panes = "A2"


def build_sources_sheet(wb):
    ws = wb.create_sheet("Sources")
    headers = ["Source", "What it's good for", "Where to get it", "Color"]
    set_widths(ws, [26, 52, 44, 12])

    for col, text in enumerate(headers, start=1):
        ws.cell(row=1, column=col, value=text)
    style_header_row(ws, 1, len(headers))

    for i, (name, good_for, where, hex_code) in enumerate(MACRO_SOURCES):
        r = 2 + i
        ws.cell(row=r, column=1, value=name).font = BOLD
        ws.cell(row=r, column=2, value=good_for)
        ws.cell(row=r, column=3, value=where)
        color_cell = ws.cell(row=r, column=4, value=hex_code)
        color_cell.fill = PatternFill("solid", fgColor=hex_code)
        color_cell.alignment = Alignment(horizontal="center")
        for col in range(1, len(headers) + 1):
            ws.cell(row=r, column=col).border = BOX

    note_row = len(MACRO_SOURCES) + 3
    ws.merge_cells(f"A{note_row}:D{note_row}")
    note = ws.cell(
        row=note_row,
        column=1,
        value=(
            "Color-code every food's Source cell. The color tells the reader how much "
            "to trust the number -- a label beats an estimate."
        ),
    )
    note.font = NOTE_FONT
    note.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[note_row].height = 30

    ws.freeze_panes = "A2"


def build_food_table_sheet(wb):
    ws = wb.create_sheet("Food Table")
    set_widths(ws, [34, 16, 12, 13, 12, 10, 24])

    for col, text in enumerate(FOOD_TABLE_HEADERS, start=1):
        ws.cell(row=FOOD_TABLE_HEADER_ROW, column=col, value=text)
    style_header_row(ws, FOOD_TABLE_HEADER_ROW, len(FOOD_TABLE_HEADERS))

    for i, food_row in enumerate(FOOD_TABLE_ROWS):
        r = FOOD_TABLE_FIRST_DATA_ROW + i
        for col, value in enumerate(food_row, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.border = BOX
            if col > 1:
                cell.alignment = Alignment(horizontal="center")
            if i % 2 == 1:
                cell.fill = BAND_FILL
        # Static source fill so the color key is visible even if a viewer
        # ignores conditional formatting (Excel/LibreOffice/Sheets all render it
        # differently). The CF rules below re-apply the same tint automatically
        # when a student changes or adds a Source.
        source = food_row[6]
        if source in SOURCE_FILLS:
            ws.cell(row=r, column=7).fill = SOURCE_FILLS[source]

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A{FOOD_TABLE_HEADER_ROW}:G{FOOD_TABLE_LAST_DATA_ROW}"

    # Source dropdown, pulled from the Sources reference tab.
    source_dv = DataValidation(
        type="list", formula1=_source_dropdown_formula(), allow_blank=True, showDropDown=False
    )
    source_dv.error = "Choose one of the six sources listed on the Sources tab."
    source_dv.errorTitle = "Unknown source"
    ws.add_data_validation(source_dv)
    source_dv.add(f"G{FOOD_TABLE_FIRST_DATA_ROW}:G{FOOD_TABLE_LAST_ROW}")

    # Conditional formatting: tint the Source cell by its value, using the same
    # hex as the static fills. One rule per source.
    cf_range = f"G{FOOD_TABLE_FIRST_DATA_ROW}:G{FOOD_TABLE_LAST_ROW}"
    for name, hex_code in SOURCE_HEX.items():
        fill = PatternFill("solid", fgColor=hex_code)
        formula = [f'$G{FOOD_TABLE_FIRST_DATA_ROW}="{name}"']
        ws.conditional_formatting.add(cf_range, FormulaRule(formula=formula, fill=fill))


def build_daily_log_sheet(wb):
    ws = wb.create_sheet("Daily Log")
    set_widths(ws, [12, 12, 34, 10, 18, 10, 10, 10, 10])

    for col, text in enumerate(DAILY_LOG_HEADERS, start=1):
        ws.cell(row=1, column=col, value=text)
    style_header_row(ws, 1, len(DAILY_LOG_HEADERS))

    for i, example in enumerate(DAILY_LOG_EXAMPLES):
        r = 2 + i
        date_str, meal, food, servings = example
        ws.cell(row=r, column=1, value=date_str)
        ws.cell(row=r, column=2, value=meal)
        ws.cell(row=r, column=3, value=food)
        ws.cell(row=r, column=4, value=servings)
        # Columns 5-9 (Source + macros) intentionally left blank -- students build these.
        for col in range(1, len(DAILY_LOG_HEADERS) + 1):
            ws.cell(row=r, column=col).border = BOX

    note_row = 6
    ws.merge_cells(f"A{note_row}:I{note_row}")
    note_cell = ws.cell(
        row=note_row,
        column=1,
        value=(
            "Build it: in each Calories / Protein / Carbs / Fat cell above, write a "
            "VLOOKUP that finds this row's Food in the Food Table, then multiply by "
            "Servings. The Source column is a second VLOOKUP -- return column 7 (the "
            "last column) instead of the macros. The Meal groups come from the old "
            "tracker template: Breakfast / Lunch / Dinner / Snacks. Once the lookups "
            "work, keep logging your own real days starting row 7."
        ),
    )
    note_cell.font = NOTE_FONT
    note_cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[note_row].height = 60

    # Food dropdown, sourced from the Food Table names (extends to row 100 so
    # students can add foods without breaking the list).
    food_dv = DataValidation(
        type="list", formula1=_food_dropdown_formula(), allow_blank=True, showDropDown=False
    )
    food_dv.error = "Choose a food from the Food Table (or add it there first)."
    food_dv.errorTitle = "Not in Food Table"
    ws.add_data_validation(food_dv)
    food_dv.add("C2:C4")
    food_dv.add(f"C7:C{DAILY_LOG_VALIDATION_ROWS + 1}")

    # Meal dropdown -- the template's meal grouping, preserved.
    meal_dv = DataValidation(
        type="list",
        formula1='"' + ",".join(MEAL_OPTIONS) + '"',
        allow_blank=True,
        showDropDown=False,
    )
    meal_dv.error = "Choose Breakfast, Lunch, Dinner, or Snacks."
    meal_dv.errorTitle = "Unknown meal"
    ws.add_data_validation(meal_dv)
    meal_dv.add("B2:B4")
    meal_dv.add(f"B7:B{DAILY_LOG_VALIDATION_ROWS + 1}")

    # Source dropdown, pulled from the Sources reference tab.
    source_dv = DataValidation(
        type="list", formula1=_source_dropdown_formula(), allow_blank=True, showDropDown=False
    )
    source_dv.error = "Choose one of the six sources listed on the Sources tab."
    source_dv.errorTitle = "Unknown source"
    ws.add_data_validation(source_dv)
    source_dv.add("E2:E4")
    source_dv.add(f"E7:E{DAILY_LOG_VALIDATION_ROWS + 1}")

    # Conditional formatting: tint the Source cell by its value (same key).
    cf_range = f"E2:E{DAILY_LOG_VALIDATION_ROWS + 1}"
    for name, hex_code in SOURCE_HEX.items():
        fill = PatternFill("solid", fgColor=hex_code)
        formula = ['$E2="' + name + '"']
        ws.conditional_formatting.add(cf_range, FormulaRule(formula=formula, fill=fill))

    ws.freeze_panes = "A2"


def build_weekly_summary_sheet(wb):
    ws = wb.create_sheet("Weekly Summary")
    headers = ["Date", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)", "Days logged"]
    set_widths(ws, [14, 12, 12, 12, 12, 14])

    ws["A1"] = "Weekly Summary"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:F1")

    ws.merge_cells("A2:F2")
    note = ws.cell(
        row=2,
        column=1,
        value=(
            "This is the weekly roll-up from the old tracker template -- now it "
            "computes itself from your log with SUMIF. Each metric cell below should be "
            "a SUMIF keyed on the Daily Log Date column (and the Days logged column a "
            "COUNTIF), so adding log rows updates this tab automatically."
        ),
    )
    note.font = NOTE_FONT
    note.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[2].height = 46

    header_row = 4
    for col, text in enumerate(headers, start=1):
        ws.cell(row=header_row, column=col, value=text)
    style_header_row(ws, header_row, len(headers))

    first_data_row = header_row + 1
    for i in range(WEEKLY_SUMMARY_DAYS):
        r = first_data_row + i
        day = WEEKLY_SUMMARY_START + timedelta(days=i)
        ws.cell(row=r, column=1, value=day.isoformat())
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=r, column=col)
            cell.border = BOX
            if col > 1:
                cell.alignment = Alignment(horizontal="center")

    last_data_row = first_data_row + WEEKLY_SUMMARY_DAYS - 1
    totals_row = last_data_row + 1
    avg_row = totals_row + 1

    ws.cell(row=totals_row, column=1, value="TOTALS").font = BOLD
    ws.cell(row=avg_row, column=1, value="Daily average").font = BOLD

    hint_row = avg_row + 2
    ws.merge_cells(f"A{hint_row}:F{hint_row}")
    hint = ws.cell(
        row=hint_row,
        column=1,
        value=(
            "Hint: the per-day metric cells are blank -- they are yours to write. "
            "Calories average = AVERAGEIF over the date-keyed Daily Log rows. The "
            "TOTALS and Daily average rows are blank too: use SUM and AVERAGE of the "
            "14 daily rows above."
        ),
    )
    hint.font = NOTE_FONT
    hint.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[hint_row].height = 46

    ws.freeze_panes = "A5"


def build_dashboard_sheet(wb):
    ws = wb.create_sheet("Dashboard")
    set_widths(ws, [24, 16, 16, 16, 44])

    ws["A1"] = "Dashboard"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:E1")

    # -- Daily Averages -----------------------------------------------------
    ws.merge_cells("A3:E3")
    ws["A3"] = "Daily Averages"
    ws["A3"].font = SECTION_FONT
    ws["A3"].fill = SECTION_FILL
    ws["A3"].alignment = Alignment(vertical="center")

    avg_headers = ["Metric", "Value", "", "", "Notes"]
    for col, text in enumerate(avg_headers, start=1):
        if text:
            ws.cell(row=4, column=col, value=text).font = BOLD

    avg_labels = [
        "Average Calories / Day",
        "Average Protein (g) / Day",
        "Average Carbs (g) / Day",
        "Average Fat (g) / Day",
    ]
    for i, label in enumerate(avg_labels):
        r = 5 + i
        ws.cell(row=r, column=1, value=label)
        ws.cell(row=r, column=2).border = BOX  # empty -- student formula goes here
        note = ws.cell(
            row=r, column=5,
            value="<- your AVERAGEIF formula goes here (Weekly Summary, keyed by date)",
        )
        note.font = NOTE_FONT

    # -- Target vs. Actual ----------------------------------------------------
    section2_row = 10
    ws.merge_cells(f"A{section2_row}:E{section2_row}")
    ws.cell(row=section2_row, column=1, value="Target vs. Actual")
    ws.cell(row=section2_row, column=1).font = SECTION_FONT
    ws.cell(row=section2_row, column=1).fill = SECTION_FILL
    ws.cell(row=section2_row, column=1).alignment = Alignment(vertical="center")

    tva_header_row = section2_row + 1
    for col, text in enumerate(["Metric", "Target", "Actual", "Difference"], start=1):
        ws.cell(row=tva_header_row, column=col, value=text).font = BOLD

    tva_labels = ["Calories", "Protein (g)", "Carbs (g)", "Fat (g)"]
    tva_first_data_row = tva_header_row + 1
    for i, label in enumerate(tva_labels):
        r = tva_first_data_row + i
        ws.cell(row=r, column=1, value=label)
        for col in (2, 3, 4):
            ws.cell(row=r, column=col).border = BOX  # empty -- student fills in
    tva_last_data_row = tva_first_data_row + len(tva_labels) - 1

    ws.cell(
        row=tva_last_data_row + 1, column=5,
        value="<- Target: your own goal. Actual: pull from Daily Averages above.",
    ).font = NOTE_FONT

    # -- Chart placeholder ------------------------------------------------
    chart_row = tva_last_data_row + 3
    ws.merge_cells(f"A{chart_row}:E{chart_row}")
    ws.cell(row=chart_row, column=1, value="Chart").font = SECTION_FONT
    ws.cell(row=chart_row, column=1).fill = SECTION_FILL
    ws.cell(row=chart_row, column=1).alignment = Alignment(vertical="center")

    note_row = chart_row + 1
    ws.merge_cells(f"A{note_row}:E{note_row + 2}")
    chart_note = ws.cell(
        row=note_row, column=1,
        value=(
            f"Insert your chart here: select A{tva_header_row}:D{tva_last_data_row} "
            "(the Target vs. Actual table), then Insert > Chart > Clustered Column. "
            "Drag the chart into the empty space below this note."
        ),
    )
    chart_note.font = NOTE_FONT
    chart_note.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[note_row].height = 50


def make_csm_p1_tracker_starter():
    wb = Workbook()
    build_read_me_sheet(wb)
    build_sources_sheet(wb)
    build_food_table_sheet(wb)
    build_daily_log_sheet(wb)
    build_weekly_summary_sheet(wb)
    build_dashboard_sheet(wb)

    out_path = os.path.join(
        REPO_ROOT, "computer-science-math", "resources", "csm-p1-tracker-starter.xlsx"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    wb.save(out_path)
    print(f"wrote {out_path}")


def main():
    make_csm_p1_tracker_starter()


if __name__ == "__main__":
    main()