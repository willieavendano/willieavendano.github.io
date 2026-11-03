# The Google Sheets driver (`scripts/drivers/sheets.py`)

> **UNTESTED-ON-DEVICE.** macOS Accessibility is not granted on the machine
> where this driver was written, so no System Events keystroke in it has ever
> been sent to a live Google Sheets session. Its pure parts (A1 maths,
> AppleScript/keystroke generation, number parsing) are covered by
> `python3 scripts/drivers/sheets.py --selftest`; everything that touches the
> app is marked *unverified* below. Budget a first run with a human watching.

## (a) Prerequisites

| Requirement | Why |
|---|---|
| **Google Chrome signed in** to the account that owns the sheet | `stage()` opens `https://sheets.new`, which lands in that account's Drive |
| **Accessibility** granted to the *host* process (Terminal / T3 Code / Ghostty) | System Events `keystroke` / `key code` is refused without it |
| **Automation** permission for Google Chrome | the driver's Chrome AppleScript (open window, read tab title) |
| **Window ≥ 1600×1000** | `stage.window`; the driver resizes the Chrome window to it |
| No other modal Sheets dialog open | keystrokes go to whatever Chrome has focused |

The driver opens a **new Chrome window** per run and closes only that window on
`teardown()` — it never quits Chrome or touches other tabs.

### Lifecycle (called by `tutorial.py`)

```
launch()                 activate Chrome (launching it if needed)
stage(window, stage)     open sheets.new, wait for "Google Sheets" in the tab
                         title, rename the file to stage.code, apply zoom,
                         create stage.sheets; returns the window size
window_title()           active-tab title — the substring OpenScreen records
perform(action, fast)    one action (base.Driver maps `range`→range_,
                         `type`→type_, `from`→from_)
read_value/read_text     Cmd-C + clipboard (see (c))
teardown(keep_open)      close this run's window only
```

`wait` and `at` are timing actions the runner handles, not the driver. Every
driver call is a single `osascript` invocation; the typing action batches its
per-character `keystroke`/`delay` lines into one call so the animation and the
pace stay in step. Logs name the action and the cell reference only — never the
clipboard contents beyond the cell being read.

The `code` used for the tab title comes from `stage["code"]` (pass it in) or the
constructor; without it the title stays "Untitled spreadsheet" and
`window_title()` still works for finding the window.

## (b) Keystroke map

Sheets (Mac) values marked **verified** are taken from Google's official list,
[*Keyboard shortcuts for Google Sheets*](https://support.google.com/docs/answer/181110)
(fetched 2026‑11). **unverified** means it is inferred (Tool finder, menu
mnemonics, or vendor lore) and has not been exercised. The Excel-for-Mac column
is offered for a future keystroke driver and is **from general knowledge, not
verified against Microsoft's list**.

| Action | Google Sheets (Mac) | Status | Excel for Mac (approx.) |
|---|---|---|---|
| Go to cell / range | `Ctrl` + `G` ("Go to range" dialog) | verified | `F5` or `Ctrl` + `G` |
| Rename sheet | Sheet menu `Option`+`Shift`+`S`, then Rename — no direct key | unverified | no default (double-click tab) |
| Rename spreadsheet | Tool finder `Option`+`/` → "Rename" | unverified | no default (Save As / title bar) |
| New sheet | `Shift`+`Fn`+`F11` (official) — driver uses Tool finder (Fn unpressable) | unverified | `Shift` + `F11` |
| Next / previous sheet | `Option`+`Down` / `Option`+`Up` (MacBook: `Option`+`Right`/`Left`) | verified | `Ctrl`+`PageDown` / `PageUp` |
| List sheets | `Option` + `Shift` + `K` | verified | none |
| Fill down | `Cmd` + `D` | verified | `Ctrl` + `D` |
| Fill right | `Cmd` + `R` | verified | `Ctrl` + `R` |
| Fill a selected range | `Cmd` + `Enter` | verified | `Ctrl` + `Enter` |
| Percent format | `Ctrl` + `Shift` + `5` | verified | `Ctrl` + `Shift` + `%` |
| Currency format | `Ctrl` + `Shift` + `4` | verified | `Ctrl` + `Shift` + `$` |
| Number (2 dp) format | `Ctrl` + `Shift` + `1` | verified | `Ctrl` + `Shift` + `!` |
| Bold | `Cmd` + `B` | verified | `Cmd` + `B` |
| Left / centre / right align | `Cmd`+`Shift`+`L` / `E` / `R` | verified | same (mac) |
| Column width / autofit | none — double-click the column border | unverified | none (Format ▸ Column Width) |
| Insert chart | Tool finder `Option`+`/` → "Chart" (no direct key) | unverified | `Fn`+`F11` (sheet) / `Alt`+`F1` (embedded) |
| Insert row above | `Cmd`+`Option`+`=` (rows selected) | verified | `Ctrl`+`Shift`+`+` (unverified on mac) |
| Insert column left | `Cmd`+`Option`+`=` (columns selected) | verified | same (unverified on mac) |
| Freeze rows/columns | none — View ▸ Freeze | unverified | none — View ▸ Freeze Panes |
| Undo | `Cmd` + `Z` | verified | `Cmd` + `Z` |
| Select all | `Cmd` + `A` (or `Cmd`+`Shift`+`Space`) | verified | `Cmd` + `A` (×2 = whole sheet) |
| Select column / row | `Ctrl`+`Space` / `Shift`+`Space` | verified | `Ctrl`+`Space` / `Shift`+`Space` |
| Zoom (legibility) | Chrome page zoom: `Cmd`+`0` reset, `Cmd`+`=` in, `Cmd`+`-` out | verified (Chrome) | no keyboard; View ▸ Zoom / status bar |
| Copy (for checks) | `Cmd` + `C` | verified | `Cmd` + `C` |
| Paste values only | `Cmd` + `Shift` + `V` | verified | `Ctrl`+`Shift`+`V` |
| Show all formulas | `Ctrl` + `~` | verified | `Ctrl` + `~` |
| Insert / edit note | `Shift` + `F2` | verified | `Shift` + `F2` |
| Open revision history | `Cmd`+`Option`+`Shift`+`H` | verified | none (File ▸ Info) |
| Search the menus | Tool finder `Option` + `/` | verified | none (uses ribbon mnemonics) |

`stage.zoom` is a **Chrome page zoom**, not a Sheets zoom: Chrome snaps to its
own ladder (`…90, 100, 110, 125, 150, 175, 200…`), so the request is rounded to
the nearest step and the driver warns when it had to. Pre-set Chrome's zoom for
`sheets.google.com` if you need an exact figure.

## (c) What the driver cannot do blind

These need a dialog, a pointer or app state that AppleScript cannot see. The
driver warns and continues; each is a candidate for the human-in-the-loop runs
below.

| Cannot do | Why | Human-in-the-loop alternative |
|---|---|---|
| **Read a cell** | Sheets has no AppleScript cell access | driver selects the cell, `Cmd`+`C`, reads `the clipboard`; the clipboard holds the cell's *content* (a **formula**, for formula cells), so numeric checks on results return `None` — mark them **unverifiable** and let the handout be the source of truth |
| **Rename sheet / spreadsheet** | no Mac shortcut; Tool finder is a guess | click the tab / title and type, or pre-name before the take |
| **Custom number codes** (e.g. `0.00000%`) | needs Format ▸ Number ▸ Custom number format | the driver applies the nearest built-in shortcut (2 dp) and warns; use the Excel driver when the exact display matters |
| **Chart type, titles, axes, anchor** | the chart editor panel is not scriptable blind | insert the default chart, then finish by hand — or record the chart scene with the Excel driver |
| **Column width / autofit** | no shortcut, no height API | double-click the column border |
| **Freeze panes** | no shortcut | View ▸ Freeze |
| **Insert / delete rows & columns** | menu-only on Mac in practice | Tool finder guess, then verify on the first run |
| **Scroll a cell to the top-left** | go-to scrolls it into view only | use the Excel driver when the framing must be exact |
| **Window / range geometry** | Sheets cannot report it | `range_rect()` returns `None`, so OpenScreen camera zooms are disabled/approximate |
| **First-run prompts** (share, sign-in, "restore pages") | app modals steal keystrokes | run once with a person to clear dialogs, or add `{ "do": "wait" }` beats |

**Human-in-the-loop options:** (1) record chart-heavy or check-heavy lessons
with the `excel` driver (reliable, no Accessibility); (2) run the `sheets`
driver with a person sitting at the keyboard to handle only the dialogs above;
(3) pre-build the workbook (charts, formats, frozen panes) in a template the
driver opens, so the take only types inputs and formulas.

## (d) Google Sheets vs Excel for this course

For the Cornerstone II / CS-Math formulas the two apps are behaviourally
identical — **PMT, MIN, INDEX and SUM all take the same arguments and return the
same values**, signs included (`PMT` is negative for a payment). Specifically:

- **Percent entry** — typing `4.5%` stores `0.045` in *both* apps and applies a
  percent display format. No difference; the driver types `%` literally.
- **`INDEX` second argument** — `INDEX(range, k)` is the *k*-th row in both
  (with an optional third argument for the column of a 2-D range). Identical.
- **Number formats** — `MIN`/`SUM` results format the same way; the only gap is
  the *custom decimal count*, which needs the dialog in Sheets (see (c)).
- **Charts** — the only real divergence: Sheets' chart editor is a side panel,
  Excel's is a ribbon dialog. The data ranges are the same; the chart-type and
  title arguments are Excel-driver territory.

Differences that *do* exist but do not touch this course: array formulas
(`ARRAYFORMULA`/dynamic arrays vs `Ctrl`+`Shift`+`Enter`), `XLOOKUP`/`FILTER`
availability, and Sparklines. If a future lesson needs those, note it in the
lesson script instead of trying to force one driver to match the other.
