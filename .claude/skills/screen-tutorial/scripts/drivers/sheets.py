"""
sheets.py — Google Sheets driver (Google Chrome + System Events)
================================================================

**UNTESTED-ON-DEVICE.** macOS Accessibility is *not* granted on the machine
where this driver was written, so every System Events keystroke path below is
best-effort and has **never been run against a live Google Sheets session**.
The pure parts — cell-reference maths, AppleScript/keystroke generation and
number parsing — have offline unit tests:

    python3 scripts/drivers/sheets.py --selftest

How it drives
-------------
There is no AppleScript dictionary for Google Sheets, so this driver:

  1. opens ``https://sheets.new`` in a **new Google Chrome window** (Chrome's
     own AppleScript, which needs Automation permission, not Accessibility),
     waits until the tab title says "Google Sheets", then
  2. sends keystrokes with ``tell application "System Events"`` — which *does*
     need Accessibility granted to the host process (Terminal / T3 Code /
     Ghostty). One ``osascript`` call per action; character-by-character
     ``keystroke`` with the script's ``pace`` for the typing animation.

Every keyboard path is taken from Google's official Mac shortcut list
(https://support.google.com/docs/answer/181110) where one exists; where it does
not (renaming a sheet or the file, inserting/deleting objects, column width,
custom number formats, the chart editor) the driver falls back to the Tool
finder (Option-/) or refuses and logs a warning. See
``references/sheets-driver.md`` for the keystroke map and the honest list of
what cannot be verified.

Prerequisites: Chrome signed into the Google account that owns the spreadsheet,
Accessibility granted to the host app, and a window at least 1600x1000.

What this driver cannot do
--------------------------
* Read a cell. Sheets has no AppleScript cell access; ``read_value`` /
  ``read_text`` select the cell, copy it (Cmd-C) and read ``the clipboard``.
  Sheets copies the cell *content* (a formula for formula cells), so numeric
  checks on formula results come back ``None`` and must be marked
  unverifiable.
* Set a custom number format, chart type/titles/axis, or column width blind.
  These need a dialog and are flagged with a warning.
* Report window/range geometry, so OpenScreen camera zooms are approximate.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import unittest
from typing import Dict, List, Optional, Sequence, Tuple

try:  # imported as part of the `drivers` package by tutorial.py
    from .base import (
        ACTIONS,
        ALIGNMENTS,
        DEFAULT_HIGHLIGHT,
        DEFAULT_PACE,
        TIMING_ACTIONS,
        Driver as BaseDriver,
        DriverError,
        num_to_col,
        parse_range,
        range_address,
        split_sheet,
    )
except ImportError:  # run directly: `python3 scripts/drivers/sheets.py --selftest`
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from base import (  # type: ignore[no-redef]
        ACTIONS,
        ALIGNMENTS,
        DEFAULT_HIGHLIGHT,
        DEFAULT_PACE,
        TIMING_ACTIONS,
        Driver as BaseDriver,
        DriverError,
        num_to_col,
        parse_range,
        range_address,
        split_sheet,
    )

SHEETS_NEW = "https://sheets.new"
DEFAULT_CHROME = "Google Chrome"
WINDOW_DEFAULT = {"width": 1600, "height": 1000}
WINDOW_MARGIN = 25  # px below the menu bar so the title bar stays clickable

PACE_COMMAND = 0.03  # s/char while typing into a dialog or the Tool finder

# System Events modifier keywords (AppleScript spellings). `ctrl` is the
# *control* key; Sheets uses Control (not Command) for most of its shortcuts.
MODIFIERS = {
    "cmd": "command down",
    "command": "command down",
    "opt": "option down",
    "option": "option down",
    "shift": "shift down",
    "ctrl": "control down",
    "control": "control down",
}

# Named keys -> macOS virtual key codes (letters go through `keystroke`).
KEY_CODES = {
    "return": 36,
    "enter": 36,
    "tab": 48,
    "escape": 53,
    "esc": 53,
    "space": 49,
    "delete": 51,
    "backspace": 51,
    "left": 123,
    "right": 124,
    "down": 125,
    "up": 126,
    "f5": 96,
    "f11": 103,
}

# Mac shortcuts verified against https://support.google.com/docs/answer/181110.
SHORTCUTS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "go_to_range":     ("g", ("ctrl",)),            # "Go to range" dialog
    "fill_down":       ("d", ("cmd",)),
    "fill_right":      ("r", ("cmd",)),
    "fill_range":      ("return", ("cmd",)),        # Fill the selected range
    "format_decimal":  ("1", ("ctrl", "shift")),
    "format_currency": ("4", ("ctrl", "shift")),
    "format_percent":  ("5", ("ctrl", "shift")),
    "bold":            ("b", ("cmd",)),
    "align_left":      ("l", ("cmd", "shift")),
    "align_center":    ("e", ("cmd", "shift")),
    "align_right":     ("r", ("cmd", "shift")),
    "undo":            ("z", ("cmd",)),
    "select_all":      ("a", ("cmd",)),
    "select_column":   ("space", ("ctrl",)),
    "select_row":      ("space", ("shift",)),
    "next_sheet":      ("down", ("opt",)),
    "prev_sheet":      ("up", ("opt",)),
    "list_sheets":     ("k", ("opt", "shift")),
    "sheet_menu":      ("s", ("opt", "shift")),
    "file_menu":       ("f", ("ctrl", "opt")),
    "edit_menu":       ("e", ("ctrl", "opt")),
    "view_menu":       ("v", ("ctrl", "opt")),
    "insert_menu":     ("i", ("ctrl", "opt")),
    "format_menu":     ("o", ("ctrl", "opt")),
    "tool_finder":     ("/", ("opt",)),             # Option-/ (search the menus)
    "copy":            ("c", ("cmd",)),
    "zoom_in":         ("=", ("cmd",)),             # Chrome page zoom
    "zoom_out":        ("-", ("cmd",)),
    "zoom_reset":      ("0", ("cmd",)),
}

# Commands Google Sheets (Mac) gives no usable keyboard shortcut for. Documented
# here so the reference table and any future Excel driver stay honest.
NO_SHORTCUT = (
    "insert_sheet",     # official is Shift-Fn-F11; System Events cannot press Fn
    "rename_sheet",
    "rename_document",
    "insert_chart",
    "freeze",
    "column_width",
    "autofit_column",
    "custom_number_format",
)

# Chrome's page-zoom ladder (Cmnd-0 resets to 100%, Cmnd-= / Cmnd-- step it).
ZOOM_LADDER = [25, 33, 50, 67, 75, 80, 90, 100, 110, 125, 150, 175, 200, 250, 300]


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested; no osascript)
# ---------------------------------------------------------------------------
def as_string(value) -> str:
    """Quote a Python value as an AppleScript string literal."""
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    text = text.replace("\n", "\\n").replace("\r", "")
    return '"' + text + '"'


def key_command(key, mods: Sequence[str] = ()) -> str:
    """One System Events statement: `keystroke` or `key code`, plus modifiers.

    ``key_command("return")            -> 'key code 36'
    ``key_command("d", ("cmd",))       -> 'keystroke "d" using {command down}'
    """
    token = str(key).lower()
    if token in KEY_CODES:
        base = "key code %d" % KEY_CODES[token]
    else:
        base = "keystroke %s" % as_string(key)
    if mods:
        return "%s using {%s}" % (base, ", ".join(MODIFIERS[m] for m in mods))
    return base


def shortcut_command(name: str) -> str:
    """The System Events statement for one named Google Sheets shortcut."""
    if name not in SHORTCUTS:
        raise KeyError("no Google Sheets shortcut named %r" % name)
    key, mods = SHORTCUTS[name]
    return key_command(key, mods)


def build_keystrokes(text, pace: float = DEFAULT_PACE) -> List[str]:
    """`keystroke`/`delay` lines that type `text` one character at a time."""
    lines: List[str] = []
    for ch in str(text):
        lines.append(key_command("return") if ch == "\n" else key_command(ch))
        if pace and pace > 0:
            lines.append("delay %.3f" % float(pace))
    return lines


def commit_command(commit) -> Optional[str]:
    """`commit` field -> the key that ends an edit ('enter', 'tab', 'none')."""
    key = {"enter": "return", "return": "return", "tab": "tab"}.get(
        (commit or "").strip().lower()
    )
    return key_command(key) if key else None


def build_action_script(lines: Sequence[str]) -> str:
    """Wrap System Events lines: activate Chrome, then run the lines."""
    out = ['tell application "Google Chrome" to activate', "delay 0.15",
           'tell application "System Events"']
    out.extend("    " + line for line in lines)
    out.append("end tell")
    return "\n".join(out)


def build_goto_script(address, pace: float = PACE_COMMAND) -> str:
    """Ctrl-G, clear the field, type the address, Return."""
    lines = [shortcut_command("go_to_range"), "delay 0.35",
             key_command("a", ("cmd",)), "delay 0.08"]
    lines += build_keystrokes(address, pace)
    lines += ["delay 0.1", key_command("return")]
    return build_action_script(lines)


def build_type_script(text, pace: float = DEFAULT_PACE, commit="enter") -> str:
    """Type `text` into the active cell and commit it."""
    lines = build_keystrokes(text, pace)
    end = commit_command(commit)
    if end:
        lines.append(end)
    return build_action_script(lines)


def tool_finder_lines(command: str, pace: float = PACE_COMMAND,
                      settle: float = 0.4) -> List[str]:
    """Open the Tool finder (Option-/), search `command`, run the first hit."""
    lines = [shortcut_command("tool_finder"), "delay %.2f" % settle]
    lines += build_keystrokes(command, pace)
    lines += ["delay 0.5", key_command("return")]
    return lines


def fill_selection(from_ref: str, range_ref: str) -> str:
    """The range Cmd-D should have selected: source rows + destination rows.

    ``fill_selection("A12:F12", "A13:F71") -> "A12:F71"``
    """
    sheet_a, (c1, r1, c2, r2) = parse_range(from_ref)
    sheet_b, (d1, dr1, d2, dr2) = parse_range(range_ref)
    if None in (r1, r2, dr1, dr2):
        return range_ref
    body = range_address((min(c1, d1), min(r1, dr1), max(c2, d2), max(r2, dr2)))
    sheet = sheet_a or sheet_b
    return "%s!%s" % (sheet, body) if sheet else body


def chart_data_range(x, series) -> Optional[str]:
    """Bounding box of the x range and every series range, for Insert > Chart."""
    refs: List[str] = []
    if isinstance(x, str) and x:
        refs.append(x)
    for item in series or []:
        ref = item.get("range") if isinstance(item, dict) else item
        if isinstance(ref, str) and ref:
            refs.append(ref)
    if not refs:
        return None
    sheet = None
    box = [None, None, None, None]
    for ref in refs:
        ref_sheet, (c1, r1, c2, r2) = parse_range(ref)
        if None in (r1, r2):
            continue
        sheet = sheet or ref_sheet
        box[0] = c1 if box[0] is None else min(box[0], c1)
        box[1] = r1 if box[1] is None else min(box[1], r1)
        box[2] = c2 if box[2] is None else max(box[2], c2)
        box[3] = r2 if box[3] is None else max(box[3], r2)
    if box[0] is None:
        return refs[0]
    body = range_address(tuple(box))
    return "%s!%s" % (sheet, body) if sheet else body


def number_format_shortcut(code) -> str:
    """Nearest built-in number-format shortcut for a format code."""
    text = str(code or "")
    if "%" in text:
        return "format_percent"
    if any(symbol in text for symbol in "$€£"):
        return "format_currency"
    return "format_decimal"


def requested_decimals(code) -> Optional[int]:
    """Decimal places asked for by a code like '0.00000%' (else None)."""
    match = re.search(r"0\.(0+)", str(code or ""))
    return len(match.group(1)) if match else None


def to_number(text) -> Optional[float]:
    """Parse a copied cell's text as a number ('4.5%' -> 0.045).

    Returns None for blanks and formulas — Sheets copies the formula, not the
    result, so a formula cell is unverifiable here.
    """
    if text is None:
        return None
    raw = str(text).strip()
    if not raw or raw.startswith("="):
        return None
    negative = raw.startswith("(") and raw.endswith(")")
    if negative:
        raw = raw[1:-1]
    percent = "%" in raw
    raw = re.sub(r"[,$€£\s]", "", raw).replace("%", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    if negative:
        value = -value
    return value / 100.0 if percent else value


def nearest_zoom(percent) -> int:
    """Chrome page-zoom step closest to `percent` (ties go to the lower step)."""
    target = int(percent)
    return min(ZOOM_LADDER, key=lambda step: (abs(step - target), step))


# ---------------------------------------------------------------------------
# The driver
# ---------------------------------------------------------------------------
class SheetsDriver(BaseDriver):
    """Drives Google Sheets through Chrome + System Events. See module docstring.

    Subclasses the shared ``drivers.base.Driver`` and implements one ``do_*``
    method per action plus the lifecycle hooks the runner calls.
    """

    name = "sheets"

    def __init__(self, log=print, pace: float = DEFAULT_PACE,
                 chrome: str = DEFAULT_CHROME, code: Optional[str] = None):
        super().__init__(log=log)
        self.pace = pace
        self.chrome = chrome
        self.code = code
        self.window = dict(WINDOW_DEFAULT)
        self._window_id: Optional[int] = None
        self._sheets: List[str] = []
        self._active_index = 0
        self._active_sheet: Optional[str] = None
        self._last_selection: Optional[str] = None
        self._warned = set()

    # -- plumbing ---------------------------------------------------------
    def _warn(self, key: str, message: str) -> None:
        """Log a warning once per `key` (never logs cell contents beyond a ref)."""
        if key in self._warned:
            return
        self._warned.add(key)
        self.log("[sheets] WARNING: %s" % message)

    def _run(self, script: str, label: str, timeout: int = 60) -> str:
        """Run one AppleScript through osascript; return stdout without the newline."""
        try:
            proc = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise DriverError(
                "sheets: %s timed out — is Accessibility granted to the host app?" % label
            )
        except OSError as err:
            raise DriverError("sheets: %s could not run osascript: %s" % (label, err))
        if proc.returncode != 0:
            raise DriverError("sheets: %s failed: %s" % (label, (proc.stderr or "").strip()[:400]))
        return proc.stdout.rstrip("\n")

    # -- lifecycle --------------------------------------------------------
    def launch(self) -> None:
        """Bring Google Chrome to the front, launching it if necessary."""
        self._run('tell application "Google Chrome" to activate', "launch Chrome")
        time.sleep(0.4)

    def _open_window(self) -> None:
        """Open a new Chrome window at sheets.new, sized to `self.window`."""
        width = int(self.window.get("width", WINDOW_DEFAULT["width"]))
        height = int(self.window.get("height", WINDOW_DEFAULT["height"]))
        bounds = "{%d, %d, %d, %d}" % (0, WINDOW_MARGIN, width, WINDOW_MARGIN + height)
        script = (
            'tell application "Google Chrome"\n'
            "    activate\n"
            "    set theWindow to make new window\n"
            "    set bounds of theWindow to " + bounds + "\n"
            "    set URL of active tab of theWindow to " + as_string(SHEETS_NEW) + "\n"
            "    return id of theWindow\n"
            "end tell"
        )
        try:
            out = self._run(script, "open sheets.new").strip()
            self._window_id = int(out) if out else None
        except (DriverError, ValueError):
            # Not fatal: the driver can still type, it just cannot close the tab.
            self._window_id = None

    def _wait_for_title(self, timeout: float = 45.0) -> str:
        """Poll the Chrome tab title until the document has loaded."""
        deadline = time.time() + timeout
        title = ""
        while time.time() < deadline:
            title = self.window_title()
            if "Google Sheets" in title:
                return title
            time.sleep(0.5)
        raise DriverError("sheets: timed out waiting for a Google Sheets document (title=%r)" % title)

    def stage(self, window, stage) -> Dict[str, int]:
        """Open sheets.new, wait, rename to `stage['code']`, zoom, create sheets.

        `window` is the size dict; `stage` is the script's `stage` object. The
        runner should pass the script `code` as `stage['code']` (or hand it to
        the constructor) if the tab title should be renamed.
        """
        stage = dict(stage or {})
        if window:
            self.window = {
                "width": int(window.get("width", WINDOW_DEFAULT["width"])),
                "height": int(window.get("height", WINDOW_DEFAULT["height"])),
            }
        self.code = stage.get("code") or self.code
        self._open_window()
        self._wait_for_title()
        time.sleep(0.8)  # let the grid paint before the first keystroke
        if self.code:
            self.rename_document(self.code)
        if stage.get("zoom"):
            self.do_zoom(int(stage["zoom"]))
        names = [str(name) for name in (stage.get("sheets") or [])]
        if names:
            self._rename_active_sheet(names[0])
            self._sheets = [names[0]]
            self._active_index = 0
            self._active_sheet = names[0]
            for name in names[1:]:
                self._insert_sheet(name)
        return self.window

    def window_title(self) -> str:
        """Chrome's active-tab title (OpenScreen uses it to find the window)."""
        try:
            return self._run(
                'tell application "Google Chrome" to get title of active tab of front window',
                "window title",
            ).strip()
        except DriverError:
            return ""

    def window_size(self) -> Tuple[int, int]:
        return (int(self.window["width"]), int(self.window["height"]))

    def teardown(self, keep_open: bool = False) -> None:
        """Close only the window this driver opened (never quits Chrome)."""
        if keep_open or self._window_id is None:
            return
        script = 'tell application "Google Chrome" to close (every window whose id is %d)' % self._window_id
        try:
            self._run(script, "close window")
        except DriverError as err:
            self._warn("teardown", str(err))
        self._window_id = None

    # -- references & navigation -----------------------------------------
    def _goto(self, ref: str) -> None:
        """Select a cell/range via the Go-to-range dialog, switching sheet first."""
        sheet, body = split_sheet(ref)
        address = ref
        if sheet and sheet in self._sheets:
            if sheet != self._active_sheet:
                self._activate_sheet(sheet)
            address = body
        self._run(build_goto_script(address), "go to %s" % ref)
        self._last_selection = ref
        time.sleep(0.15)

    def _activate_sheet(self, name: str) -> None:
        """Step to a tracked sheet with Option-Down / Option-Up."""
        index = self._sheets.index(name)
        delta = index - self._active_index
        if delta:
            shortcut = "next_sheet" if delta > 0 else "prev_sheet"
            lines: List[str] = []
            for _ in range(abs(delta)):
                lines += [shortcut_command(shortcut), "delay 0.2"]
            self._run(build_action_script(lines), "activate sheet %s" % name)
            self._active_index = index
        self._active_sheet = name

    def _insert_sheet(self, name: str) -> None:
        """Insert a sheet (Tool finder > Insert sheet) and rename it.

        UNVERIFIED: the official shortcut is Shift-Fn-F11, but System Events
        cannot press Fn, so the Tool finder is the fallback.
        """
        self._run(build_action_script(tool_finder_lines("Insert sheet")), "insert sheet")
        time.sleep(0.6)
        self._rename_active_sheet(name)
        self._sheets.append(name)
        self._active_index = len(self._sheets) - 1
        self._active_sheet = name

    def _rename_active_sheet(self, name: str) -> None:
        """Rename the active sheet (Tool finder > Rename sheet). UNVERIFIED."""
        lines = tool_finder_lines("Rename sheet")
        lines += [key_command("a", ("cmd",)), "delay 0.1"]
        lines += build_keystrokes(name, PACE_COMMAND)
        lines += ["delay 0.1", key_command("return")]
        self._run(build_action_script(lines), "rename sheet")
        time.sleep(0.3)

    def rename_document(self, name: str) -> None:
        """Rename the spreadsheet (tab title) via the Tool finder.

        UNVERIFIED: the Tool finder may list both "Rename" (the file) and
        "Rename sheet"; if the wrong entry wins, rename by hand or pre-set the
        title before the take.
        """
        lines = tool_finder_lines("Rename")
        lines += [key_command("a", ("cmd",)), "delay 0.1"]
        lines += build_keystrokes(name, PACE_COMMAND)
        lines += ["delay 0.1", key_command("return")]
        self._run(build_action_script(lines), "rename document")
        time.sleep(0.3)

    # -- actions (do_*) ---------------------------------------------------
    def do_sheet(self, name, fast=False):
        """Activate the named sheet, creating it (at the end) if needed."""
        if name in self._sheets:
            self._activate_sheet(name)
        else:
            self._insert_sheet(name)
        self._active_sheet = name

    def do_rename_sheet(self, from_, to, fast=False):
        """Rename a worksheet, activating it first if it is tracked."""
        if from_ in self._sheets:
            self._activate_sheet(from_)
        self._rename_active_sheet(to)
        if from_ in self._sheets:
            self._sheets[self._sheets.index(from_)] = to
        self._active_sheet = to

    def do_select(self, cell=None, range_=None, fast=False):
        """Select a cell or range (Go-to-range dialog; also scrolls it in view)."""
        target = cell or range_
        if not target:
            raise DriverError("sheets: select needs 'cell' or 'range'")
        self._goto(target)

    def do_type(self, cell, text, pace=DEFAULT_PACE, commit="enter", fast=False):
        """Select the cell, type `text` character by character, then commit.

        UNVERIFIED on device. Text beginning with '=' is typed as a formula.
        """
        self._goto(cell)
        use_pace = 0.0 if fast else float(pace)
        self._run(build_type_script(text, use_pace, commit), "type %s" % cell)
        time.sleep(0.1)

    def do_set(self, cell=None, range_=None, value=None, formula=None, fast=False):
        """Write a value/formula with no animation (fast keystrokes, pace 0).

        With a range, commits with Cmd-Enter ("Fill range") so every cell gets
        the value.
        """
        target = cell or range_
        if not target:
            raise DriverError("sheets: set needs 'cell' or 'range'")
        if formula is not None:
            text = str(formula)
            if not text.startswith("="):
                text = "=" + text
        elif value is not None:
            text = str(value)
        else:
            raise DriverError("sheets: set needs 'value' or 'formula'")
        self._goto(target)
        lines = build_keystrokes(text, 0.0)
        if range_ and not cell:
            lines.append(key_command("return", ("cmd",)))  # Fill range
        else:
            lines.append(key_command("return"))
        self._run(build_action_script(lines), "set %s" % target)
        time.sleep(0.1)

    def do_fill_down(self, range_, from_, fast=False):
        """Copy `from_` down through `range_` with Cmd-D (autofill)."""
        selection = fill_selection(from_, range_) if from_ else range_
        self._goto(selection)
        self._run(build_action_script([shortcut_command("fill_down")]), "fill down %s" % selection)
        time.sleep(0.2)

    def do_format(self, range_, number=None, bold=None, width=None, align=None, fast=False):
        """Bold / align / number-format a range.

        `width` cannot be driven blind (see module docstring) and only warns.
        """
        self._goto(range_)
        lines: List[str] = []
        if bold:
            lines.append(shortcut_command("bold"))
        if align:
            key = "align_" + str(align).lower()
            if align not in ALIGNMENTS:
                self._warn("align", "unknown align %r (left/center/right)" % (align,))
            else:
                lines.append(shortcut_command(key))
        if lines:
            self._run(build_action_script(lines), "format %s" % range_)
        if number:
            self._apply_number_format(range_, number, fast)
        if width is not None:
            self._warn(
                "width",
                "column width/autofit has no keyboard path in Sheets; the column keeps "
                "its default width — mark width-dependent pixel checks unverifiable",
            )
        time.sleep(0.1)

    def _apply_number_format(self, range_, code, fast: bool = False) -> None:
        """Built-in shortcut for the code's family; custom codes also warn."""
        shortcut = number_format_shortcut(code)
        self._run(build_action_script([shortcut_command(shortcut)]),
                  "number format %s" % range_)
        decimals = requested_decimals(code)
        if decimals not in (None, 2):
            self._warn(
                "custom-format",
                "exact code %r needs Format > Number > Custom number format; applied the "
                "%s shortcut and will mark display-text checks unverifiable" % (code, shortcut),
            )
            if not fast:
                self._apply_custom_number_format(code)

    def _apply_custom_number_format(self, code) -> None:
        """Best-effort custom format via Tool finder. UNVERIFIED."""
        lines = tool_finder_lines("Custom number format")
        lines += [key_command("a", ("cmd",)), "delay 0.1"]
        lines += build_keystrokes(code, PACE_COMMAND)
        lines += ["delay 0.1", key_command("return")]
        try:
            self._run(build_action_script(lines), "custom number format")
        except DriverError as err:
            self._warn("custom-format-failed", str(err))

    def do_header_row(self, row, values, bold=True, fast=False):
        """Type headers across row `row` from column A, then bold them."""
        values = list(values or [])
        self._goto("A%s" % row)
        pace = 0.0 if fast else self.pace
        lines: List[str] = []
        for index, value in enumerate(values):
            lines += build_keystrokes(str(value), pace)
            if index < len(values) - 1:
                lines.append(key_command("tab"))
        if lines:
            self._run(build_action_script(lines), "header row %s" % row)
        if bold and values:
            last = num_to_col(len(values))
            self._goto("A%s:%s%s" % (row, last, row))
            self._run(build_action_script([shortcut_command("bold")]), "bold header")

    def do_chart(self, type_, series, x=None, title=None, x_title=None, y_title=None,
                 at=None, size=None, y_min=None, fast=False):
        """Best-effort chart: select the data, Insert > Chart, leave it.

        The chart editor cannot be driven blind, so `type`/titles/axis/`at`/
        `size`/`y_min` are ignored with a warning. See references/sheets-driver.md.
        """
        data = chart_data_range(x, series)
        if data:
            self._goto(data)
        self._run(build_action_script(tool_finder_lines("Chart")), "insert chart")
        time.sleep(1.5)
        ignored = [
            name for name, value in (
                ("type", type_), ("title", title), ("x_title", x_title),
                ("y_title", y_title), ("y_min", y_min), ("at", at), ("size", size),
            ) if value is not None
        ]
        self._warn(
            "chart-editor",
            "inserted a default chart from %s; cannot set %s blind (chart editor) — "
            "use the excel driver or finish the chart by hand"
            % (data, ", ".join(ignored) or "chart options"),
        )

    def do_scroll(self, cell, fast=False):
        """Bring `cell` into view. Sheets has no scroll-to-corner command."""
        self._goto(cell)
        self._warn(
            "scroll",
            "Sheets cannot scroll a cell to the top-left corner; go-to only brings "
            "%s into view" % cell,
        )

    def do_zoom(self, percent, fast=False):
        """Chrome page zoom (Cmnd-0 reset, then Cmnd-= / Cmnd-- to the nearest step)."""
        target = nearest_zoom(percent)
        if target != int(percent):
            self._warn("zoom-ladder", "Chrome page zoom snaps to %d%% (nearest to %s%%)"
                       % (target, percent))
        base = ZOOM_LADDER.index(100)
        index = ZOOM_LADDER.index(target)
        lines = [shortcut_command("zoom_reset"), "delay 0.15"]
        step = "zoom_in" if index > base else "zoom_out"
        for _ in range(abs(index - base)):
            lines += [shortcut_command(step), "delay 0.12"]
        self._run(build_action_script(lines), "zoom %d%%" % target)
        time.sleep(0.2)

    def do_highlight(self, range_, seconds=DEFAULT_HIGHLIGHT, fast=False):
        """Select `range_` for emphasis, then restore the previous selection."""
        previous = self._last_selection
        self._goto(range_)
        if not fast:
            time.sleep(max(0.0, float(seconds)))
        if previous:
            self._goto(previous)

    # -- checks -----------------------------------------------------------
    def _copy_cell(self, ref: str) -> None:
        """Select one cell and copy it (Cmd-C) so the clipboard holds its text."""
        self._goto(ref)
        self._run(build_action_script([key_command("c", ("cmd",))]), "copy %s" % ref)
        time.sleep(0.25)

    def _clipboard_text(self) -> str:
        """The plain-text clipboard. Empty on error (non-text clipboard)."""
        script = 'try\n    return (the clipboard as text)\non error\n    return ""\nend try'
        try:
            return self._run(script, "clipboard")
        except DriverError:
            return ""

    def read_text(self, ref):
        """Sheets puts the cell *content* (a formula for formula cells) on the
        clipboard — not the displayed string. Display-text checks are
        unverifiable through this driver.
        """
        self._copy_cell(ref)
        return self._clipboard_text()

    def read_value(self, ref):
        """Best-effort numeric value parsed from the copied cell content.

        A formula cell copies its formula, so this returns None and the check
        must be marked unverifiable.
        """
        text = self.read_text(ref)
        value = to_number(text)
        if value is None and str(text).startswith("="):
            self._warn(
                "read-formula",
                "read_value(%s): clipboard holds a formula, not its result — mark the "
                "check unverifiable" % ref,
            )
        return value


# The runner may look the class up by the module-level name `Driver`.
Driver = SheetsDriver  # noqa: E305  (intentional alias, see module docstring)


# ---------------------------------------------------------------------------
# Offline self-tests (pure parts only — no Chrome, no Accessibility)
# ---------------------------------------------------------------------------
class _Recorder(SheetsDriver):
    """A driver that records AppleScript instead of running it."""

    def __init__(self):
        super().__init__(log=lambda *args: None)
        self.scripts: List[Tuple[str, str]] = []

    def _run(self, script, label, timeout=60):
        self.scripts.append((label, script))
        return ""

    def joined(self) -> str:
        return "\n".join(script for _, script in self.scripts)


class SheetsDriverTests(unittest.TestCase):
    def test_a1_grammar_delegates_to_base(self):
        self.assertEqual(parse_range("A12:F71")[1], (1, 12, 6, 71))
        self.assertEqual(parse_range("Savings!B6")[1], (2, 6, 2, 6))

    def test_fill_selection_unions_source_and_destination(self):
        self.assertEqual(fill_selection("A12:F12", "A13:F71"), "A12:F71")
        self.assertEqual(
            fill_selection("Savings!A2:D2", "Savings!A3:D20"), "Savings!A2:D20"
        )

    def test_chart_data_range_bounds_every_series(self):
        series = [{"range": "B2:B10", "name": "n"}, "C2:C10"]
        self.assertEqual(chart_data_range("A2:A10", series), "A2:C10")
        self.assertIsNone(chart_data_range(None, []))

    def test_applescript_string_escaping(self):
        self.assertEqual(as_string('He said "hi"'), '"He said \\"hi\\""')
        self.assertEqual(as_string("a\\b"), '"a\\\\b"')

    def test_key_and_shortcut_commands(self):
        self.assertEqual(key_command("return"), "key code 36")
        self.assertEqual(key_command("d", ("cmd",)), 'keystroke "d" using {command down}')
        self.assertEqual(key_command("%"), 'keystroke "%"')
        self.assertEqual(shortcut_command("go_to_range"), 'keystroke "g" using {control down}')
        self.assertEqual(shortcut_command("fill_range"), "key code 36 using {command down}")

    def test_build_keystrokes_has_pace_between_chars(self):
        self.assertEqual(
            build_keystrokes("A1", 0.045),
            ['keystroke "A"', "delay 0.045", 'keystroke "1"', "delay 0.045"],
        )
        self.assertEqual(build_keystrokes("A1", 0.0), ['keystroke "A"', 'keystroke "1"'])

    def test_goto_script_uses_ctrl_g(self):
        script = build_goto_script("Savings!B6")
        self.assertIn('keystroke "g" using {control down}', script)
        self.assertIn('keystroke "B"', script)
        self.assertTrue(script.rstrip().endswith("end tell"))

    def test_tool_finder_opens_with_option_slash(self):
        lines = tool_finder_lines("Chart")
        self.assertEqual(lines[0], 'keystroke "/" using {option down}')
        self.assertEqual(lines[-1], "key code 36")

    def test_to_number(self):
        self.assertAlmostEqual(to_number("4.5%"), 0.045)
        self.assertAlmostEqual(to_number("$1,234.50"), 1234.5)
        self.assertAlmostEqual(to_number("(12.5)"), -12.5)
        self.assertIsNone(to_number("=SUM(A1:A3)"))
        self.assertIsNone(to_number("hello"))
        self.assertIsNone(to_number(""))

    def test_number_format_family_and_decimals(self):
        self.assertEqual(number_format_shortcut("0.00000%"), "format_percent")
        self.assertEqual(number_format_shortcut("$#,##0.00"), "format_currency")
        self.assertEqual(number_format_shortcut("#,##0"), "format_decimal")
        self.assertEqual(requested_decimals("0.00000%"), 5)
        self.assertEqual(requested_decimals("$#,##0.00"), 2)

    def test_nearest_zoom(self):
        self.assertEqual(nearest_zoom(160), 150)
        self.assertEqual(nearest_zoom(200), 200)
        self.assertEqual(nearest_zoom(100), 100)

    def test_shortcut_table_is_well_formed(self):
        for name, (key, mods) in SHORTCUTS.items():
            self.assertIsInstance(key, str, name)
            for mod in mods:
                self.assertIn(mod, MODIFIERS, name)

    def test_every_action_in_script_format_is_implemented(self):
        expected = set(ACTIONS) - TIMING_ACTIONS
        base_methods = {name[3:] for name in dir(BaseDriver) if name.startswith("do_")}
        for do in expected:
            method = getattr(SheetsDriver, "do_" + do)
            self.assertIsNot(
                method, getattr(BaseDriver, "do_" + do),
                "SheetsDriver does not override do_%s" % do,
            )
        self.assertEqual(base_methods, expected)

    def test_fill_down_perform_selects_the_union(self):
        rec = _Recorder()
        rec.perform({"do": "fill_down", "range": "A13:F71", "from": "A12:F12"})
        self.assertTrue(any("A12:F71" in label for label, _ in rec.scripts))

    def test_type_perform_types_and_commits(self):
        rec = _Recorder()
        rec.perform({"do": "type", "cell": "B6", "text": "=1+1"})
        script = rec.joined()
        self.assertIn('keystroke "="', script)
        self.assertIn("key code 36", script)

    def test_set_on_range_fills_the_range(self):
        rec = _Recorder()
        rec.perform({"do": "set", "range": "B2:B10", "value": "0"})
        self.assertIn("key code 36 using {command down}", rec.joined())

    def test_zoom_snaps_to_ladder(self):
        rec = _Recorder()
        rec.perform({"do": "zoom", "percent": 160})
        self.assertTrue(any(label == "zoom 150%" for label, _ in rec.scripts))


def _run_selftest() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="sheets.py",
        description="Google Sheets driver for the screen-tutorial pipeline "
                    "(UNTESTED-ON-DEVICE; --selftest covers the pure parts).",
    )
    parser.add_argument("--selftest", action="store_true",
                        help="run the driver's offline unit tests and exit")
    args = parser.parse_args(argv)
    if args.selftest:
        return _run_selftest()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
