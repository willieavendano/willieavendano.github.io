"""Microsoft Excel for Mac driver — AppleScript through `osascript`.

Implements the action vocabulary of `references/script-format.md § Actions`
using only Excel's own AppleScript dictionary: no System Events keystrokes,
so it works without the Accessibility permission (only Automation, which
macOS prompts for once).

How the "typing" effect works: the cell is selected and its content is set to
the partial text with a leading apostrophe ('=(1+B, '=(1+B3 ...), one
`set formula` per character with a short `delay`; the apostrophe makes Excel
show the fragment as literal text. At the end the real entry is committed
with `set formula`, which Excel parses exactly like typed input ("4.5%"
becomes 0.045 formatted as a percent, "$500" becomes 500 as currency,
"=..." becomes a formula). One osascript call per action, not per character.

Verified on Excel 16.114 (2026-11): fill down, `goto ... with scroll`,
`string value` (the displayed text), charts with `set source data`,
`make new series`, chart and axis titles, `minimum scale`.
"""

import subprocess
import time

from .base import (DEFAULT_HIGHLIGHT, DEFAULT_PACE, Driver, DriverError,
                   num_to_col, parse_range, range_address, split_sheet)

APP = "Microsoft Excel"
LAUNCH_TIMEOUT = 150     # s; Excel's first launch after login can take ~60 s
MENU_BAR = 25            # pt; windows are placed just under the menu bar
BOTTOM_CHROME = 46       # pt; sheet tabs + status bar under the grid


def q(text):
    """AppleScript string literal."""
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def as_literal(value):
    """Python value -> AppleScript literal (numbers, booleans, strings, lists)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "{" + ", ".join(as_literal(v) for v in value) + "}"
    if value is None:
        return '""'
    return q(value)


def run_osascript(script, timeout=60):
    """Run an AppleScript; return its stdout (stripped). Raise DriverError."""
    try:
        proc = subprocess.run(["osascript", "-"], input=script, capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise DriverError("osascript timed out after %ss" % timeout)
    if proc.returncode != 0:
        raise DriverError(proc.stderr.strip() or "osascript failed")
    return proc.stdout.strip()


class ExcelDriver(Driver):
    """Drives one new, unsaved workbook in Microsoft Excel."""

    name = "excel"

    def __init__(self, log=print):
        super().__init__(log)
        self.workbook = None        # e.g. "Book3"; set by stage()
        self.active = None          # name of the active worksheet
        self._size = None           # (w, h) of the window after staging

    # -- plumbing ------------------------------------------------------------
    def _run(self, body, timeout=60):
        """Run AppleScript statements inside `tell application "Microsoft Excel"`
        with `wb` bound to this session's workbook."""
        head = "tell application %s\n" % q(APP)
        if self.workbook:
            head += "set wb to workbook %s\n" % q(self.workbook)
        return run_osascript(head + body + "\nend tell\n", timeout=timeout)

    def _sheet_expr(self, sheet):
        return "worksheet %s of wb" % q(sheet) if sheet else "active sheet"

    def _range_expr(self, ref):
        """'Savings!B6' -> range "B6" of worksheet "Savings" of wb"""
        sheet, body = split_sheet(ref)
        return "range %s of %s" % (q(body), self._sheet_expr(sheet))

    def _activate_for(self, ref):
        """Visible actions on another sheet first bring that sheet forward."""
        sheet, _ = split_sheet(ref)
        if sheet and sheet != self.active:
            self.do_sheet(sheet)

    def _local(self, ref):
        """Strip the sheet: 'Savings!B6' -> 'B6'."""
        return split_sheet(ref)[1]

    # -- lifecycle -------------------------------------------------------------
    def launch(self):
        """Start Excel and wait until it answers AppleScript."""
        deadline = time.time() + LAUNCH_TIMEOUT
        run_osascript('tell application %s to activate' % q(APP), timeout=LAUNCH_TIMEOUT)
        while True:
            try:
                run_osascript('tell application %s to count of workbooks' % q(APP), timeout=30)
                return
            except DriverError as err:
                if time.time() > deadline:
                    raise DriverError("Excel did not become scriptable: %s" % err)
                time.sleep(3)

    def stage(self, window, stage):
        """New workbook; worksheets from stage.sheets; window size; zoom."""
        width = int(window.get("width", 1600))
        height = int(window.get("height", 1000))
        sheets = list(stage.get("sheets") or [])
        zoom = int(stage.get("zoom", 100))
        out = run_osascript(
            "tell application %s\n" % q(APP)
            + "activate\nset wb to make new workbook\nreturn name of wb\nend tell")
        self.workbook = out
        body = []
        if sheets:
            body.append("set name of worksheet 1 of wb to %s" % q(sheets[0]))
            for name in sheets[1:]:
                body.append("set ws to make new worksheet at end of wb")
                body.append("set name of ws to %s" % q(name))
            body.append("activate object worksheet %s of wb" % q(sheets[0]))
        # macOS clamps the bounds to the screen; read them back.
        body.append("set bounds of window 1 to {0, %d, %d, %d}" % (MENU_BAR, width, MENU_BAR + height))
        body.append("set zoom of active window to %d" % zoom)
        body.append("select range \"A1\" of active sheet")
        body.append("set b to bounds of window 1")
        body.append("return ((item 3 of b) - (item 1 of b) as string) & \",\" & "
                    "((item 4 of b) - (item 2 of b) as string) & \",\" & (name of active sheet)")
        w, h, active = self._run("\n".join(body)).split(",", 2)
        self._size = (int(float(w)), int(float(h)))
        self.active = active
        if self._size != (width, height):
            self.log("  note: window clamped by the screen to %dx%d (asked %dx%d)"
                     % (self._size + (width, height)))

    def window_title(self):
        return self._run("return name of window 1")

    def window_size(self):
        return self._size

    def bring_to_front(self):
        self._run("activate")

    def teardown(self, keep_open=False):
        if not self.workbook or keep_open:
            return
        try:
            self._run("close wb saving no")
        except DriverError as err:
            self.log("  warning: could not close %s: %s" % (self.workbook, err))
        self.workbook = None

    # -- reading (checks) ----------------------------------------------------
    def read_value(self, ref):
        """Numeric value if the cell holds a number, else its text.

        `value of range` comes back rounded to the cell's display precision
        when the cell carries a number format (a $#,##0.00 cell holding
        1.8374047 reads as 1.8374), so numbers are read through Excel's own
        TEXT() via `evaluate name`, which keeps full precision. Text cells
        fall through to the plain read.
        """
        sheet, body = split_sheet(ref)
        sheet = sheet or self.active
        if sheet:
            full = "'%s'!%s" % (sheet.replace("'", "''"), body)
            expr = 'TEXT(%s,"0.##############")' % full
            try:
                raw = self._run("return (evaluate name %s)" % q(expr))
                return float(raw)
            except (ValueError, DriverError, OSError):
                pass
        raw = self._run("return value of %s" % self._range_expr(ref))
        try:
            return float(raw)
        except ValueError:
            return raw

    def read_text(self, ref):
        """What the student sees in the cell (Excel's displayed string)."""
        return self._run("return string value of %s" % self._range_expr(ref))

    def visible_box(self):
        addr = self._run("return get address of (visible range of active window)")
        return parse_range(addr)[1]

    def range_rect(self, ref):
        """Approximate rectangle of `ref` inside the window, as fractions.

        Excel reports a range's `left position`/`top` in points on the sheet
        (100% zoom, origin at A1). We subtract the visible top-left cell's
        position, scale by the zoom, and add the window chrome (ribbon,
        formula bar, headers) estimated as window size minus `usable` size.
        Good to a few percent, which is all a camera zoom needs.
        """
        if not self._size:
            return None
        rng = self._range_expr(ref)
        out = self._run(
            "set vr to visible range of active window\n"
            "set tl to cell 1 of vr\n"
            "set r to %s\n" % rng
            + "return (left position of r as string) & \",\" & (top of r as string) & \",\" & "
            "(width of r as string) & \",\" & (height of r as string) & \",\" & "
            "(left position of tl as string) & \",\" & (top of tl as string) & \",\" & "
            "(zoom of active window as string) & \",\" & "
            "(usable width of active window as string) & \",\" & "
            "(usable height of active window as string)")
        left, top, w, h, vl, vt, zoom, uw, uh = (float(v) for v in out.split(","))
        win_w, win_h = self._size
        z = zoom / 100.0
        # Chrome: what the window has that the grid area does not. The ribbon
        # and formula bar sit above the grid, the sheet tabs + status bar
        # (~46 pt) below it, the row headers (~24 pt at 100%) at the left and
        # the column headers (~18 pt at 100%) on top. Calibrated against a
        # screenshot at zoom 160 on a 1600x923 window: within ~1% of the truth.
        x0 = max(0.0, win_w - uw) + 24 * z
        y0 = max(0.0, win_h - uh - BOTTOM_CHROME) + 18 * z
        x = x0 + (left - vl) * z
        y = y0 + (top - vt) * z
        return (x / win_w, y / win_h, w * z / win_w, h * z / win_h)

    # -- actions ----------------------------------------------------------------
    def do_sheet(self, name, fast=False):
        """Activate the worksheet, creating it at the end if it is missing."""
        self._run(
            "if not (exists worksheet %s of wb) then\n" % q(name)
            + "set ws to make new worksheet at end of wb\n"
            "set name of ws to %s\n" % q(name)
            + "end if\nactivate object worksheet %s of wb" % q(name))
        self.active = name

    def do_rename_sheet(self, from_, to, fast=False):
        self._run("set name of worksheet %s of wb to %s" % (q(from_), q(to)))
        if self.active == from_:
            self.active = to

    def _ensure_visible(self, box, margin=2):
        """Scroll only if the range is outside the visible area."""
        try:
            vis = self.visible_box()
        except DriverError:
            return
        c1, r1, c2, r2 = box
        r2 = r2 or r1
        c2 = c2 or c1
        if vis[0] <= c1 and c2 <= vis[2] - 1 and vis[1] <= r1 and r2 <= vis[3] - 1:
            return
        row = max(1, r1 - margin) if (r1 < vis[1] or r2 > vis[3] - 1) else vis[1]
        col = max(1, c1 - 1) if (c1 < vis[0] or c2 > vis[2] - 1) else vis[0]
        self._run("set scroll row of active window to %d\nset scroll column of active window to %d"
                  % (row, col))

    def ensure_visible(self, ref):
        self._activate_for(ref)
        self._ensure_visible(parse_range(ref)[1])

    def do_select(self, cell=None, range_=None, fast=False):
        ref = cell or range_
        self._activate_for(ref)
        self._ensure_visible(parse_range(ref)[1])
        self._run("select %s" % self._range_expr(ref))

    def _commit_move(self, ref, commit):
        """Where the selection goes after committing, like the real keys."""
        sheet, (c, r, _, _) = parse_range(ref)
        if commit == "enter":
            nxt = "%s%d" % (num_to_col(c), r + 1)
        elif commit == "tab":
            nxt = "%s%d" % (num_to_col(c + 1), r)
        else:
            return ""
        return "select range %s of %s" % (q(nxt), self._sheet_expr(sheet))

    def do_type(self, cell, text, pace=DEFAULT_PACE, commit="enter", fast=False):
        """Show `text` appearing in `cell` character by character, then commit."""
        text = str(text)
        self._activate_for(cell)
        self._ensure_visible(parse_range(cell)[1])
        rng = self._range_expr(cell)
        lines = ["set r to %s" % rng, "select r"]
        if not fast:
            pace = max(0.0, float(pace))
            for i in range(1, len(text) + 1):
                lines.append("set formula of r to %s" % q("'" + text[:i]))
                lines.append("delay %.3f" % pace)
        lines.append("set formula of r to %s" % q(text))
        move = self._commit_move(cell, commit)
        if move:
            lines.append(move)
        self._run("\n".join(lines), timeout=60 + len(text) * 2)

    def do_set(self, cell=None, range_=None, value=None, formula=None, fast=False):
        """Instant write. A formula into a multi-cell range is written to the
        top-left cell and filled right/down, so relative references adjust."""
        ref = cell or range_
        sheet, box = parse_range(ref)
        c1, r1, c2, r2 = box
        if formula is not None:
            first = "%s%d" % (num_to_col(c1), r1)
            ws = self._sheet_expr(sheet)
            lines = ["set formula of range %s of %s to %s" % (q(first), ws, q(formula))]
            if c2 and c2 > c1:
                lines.append("fill right range %s of %s" % (q(range_address((c1, r1, c2, r1))), ws))
            if r2 and r2 > r1:
                lines.append("fill down range %s of %s" % (q(range_address(box)), ws))
            self._run("\n".join(lines))
        else:
            self._run("set value of %s to %s" % (self._range_expr(ref), as_literal(value)))

    def do_fill_down(self, range_, from_, fast=False):
        """Copy the formulas in `from_` (one row) down through `range_`."""
        sheet_r, (c1, r1, c2, r2) = parse_range(range_)
        sheet_f, (fc1, fr1, fc2, fr2) = parse_range(from_)
        sheet = sheet_r or sheet_f
        if (fc1, fc2) != (c1, c2) or not (fr2 + 1 == r1 or fr1 == r1):
            raise DriverError("fill_down: `from` %s must be the row directly above %s "
                              "with the same columns" % (from_, range_))
        if fr1 != fr2:
            raise DriverError("fill_down: `from` must be a single row, got %s" % from_)
        whole = range_address((c1, fr1, c2, r2))
        ws = self._sheet_expr(sheet)
        if sheet:
            self._activate_for(range_)
        lines = []
        if not fast:
            lines += ["select range %s of %s" % (q(whole), ws), "delay 0.35"]
        lines.append("fill down range %s of %s" % (q(whole), ws))
        self._run("\n".join(lines))

    def do_format(self, range_, number=None, bold=None, width=None, align=None, fast=False):
        rng = self._range_expr(range_)
        lines = ["set r to %s" % rng]
        if number is not None:
            lines.append("set number format of r to %s" % q(number))
        if bold is not None:
            lines.append("set bold of font object of r to %s" % as_literal(bool(bold)))
        if width is not None:
            lines.append("set column width of (entire column of r) to %s" % float(width))
        if align is not None:
            if align not in ("left", "center", "right"):
                raise DriverError("format: align must be left, center or right")
            lines.append("set horizontal alignment of r to horizontal align %s" % align)
        self._run("\n".join(lines))

    def do_header_row(self, row, values, bold=True, fast=False):
        """Write a row of headers from column A, one cell at a time on screen."""
        row = int(row)
        last = num_to_col(len(values))
        lines = []
        if fast:
            lines.append("set value of range %s of active sheet to {%s}"
                         % (q("A%d:%s%d" % (row, last, row)), as_literal(list(values))))
        else:
            for i, v in enumerate(values, start=1):
                lines.append("set value of range %s of active sheet to %s"
                             % (q("%s%d" % (num_to_col(i), row)), as_literal(v)))
                lines.append("delay 0.08")
        if bold:
            lines.append("set bold of font object of range %s of active sheet to true"
                         % q("A%d:%s%d" % (row, last, row)))
        self._run("\n".join(lines))

    def _absolute(self, ref, default_sheet):
        """'A13:A20' -> "='Savings'!$A$13:$A$20" for chart series formulas."""
        sheet, box = parse_range(ref)
        sheet = sheet or default_sheet
        c1, r1, c2, r2 = box
        a = "$%s$%d" % (num_to_col(c1), r1)
        b = "$%s$%d" % (num_to_col(c2), r2)
        return "='%s'!%s:%s" % (sheet.replace("'", "''"), a, b)

    def do_chart(self, type_, series, x=None, title=None, x_title=None, y_title=None,
                 at=None, size=None, y_min=None, fast=False):
        """Insert a line or column chart anchored at cell `at`."""
        chart_type = {"line": "line chart", "column": "column clustered"}.get(type_)
        if not chart_type:
            raise DriverError("chart: type must be line or column")
        sheet = split_sheet(at)[0] if at else None
        sheet = sheet or self.active
        ws = self._sheet_expr(sheet)
        w, h = (size or [480, 300])[:2]
        anchor = self._local(at) if at else "H2"
        lines = [
            "set ws to %s" % ws,
            "set a to range %s of ws" % q(anchor),
            "set co to make new chart object at ws with properties "
            "{left position:(left position of a), top:(top of a), width:%s, height:%s}" % (w, h),
            "set ch to chart of co",
            "set chart type of ch to %s" % chart_type,
        ]
        for i, s in enumerate(series, start=1):
            values = self._absolute(s["range"], sheet)
            if i == 1:
                s_sheet, s_body = split_sheet(s["range"])
                lines.append("set source data ch source (range %s of %s)"
                             % (q(s_body), self._sheet_expr(s_sheet or sheet)))
                lines.append("set series values of series 1 of ch to %s" % q(values))
            else:
                lines.append("make new series at ch with properties {series values:%s}" % q(values))
            if s.get("name"):
                lines.append("set name of series %d of ch to %s" % (i, q(s["name"])))
            if x:
                lines.append("set xvalues of series %d of ch to %s" % (i, q(self._absolute(x, sheet))))
        if title:
            lines += ["set has title of ch to true",
                      "set caption of chart title of ch to %s" % q(title)]
        if y_title or y_min is not None:
            lines.append("set ax to get axis ch axis type value axis which axis primary axis")
            if y_title:
                lines += ["set has title of ax to true",
                          "set caption of axis title of ax to %s" % q(y_title)]
            if y_min is not None:
                lines.append("set minimum scale of ax to %s" % float(y_min))
        if x_title:
            lines += ["set cx to get axis ch axis type category axis which axis primary axis",
                      "set has title of cx to true",
                      "set caption of axis title of cx to %s" % q(x_title)]
        self._run("\n".join(lines))

    def do_scroll(self, cell, fast=False):
        """Scroll so `cell` is the top-left visible cell."""
        self._activate_for(cell)
        c, r = parse_range(cell)[1][:2]
        self._run("set scroll row of active window to %d\nset scroll column of active window to %d"
                  % (r, c))

    def do_zoom(self, percent, fast=False):
        self._run("set zoom of active window to %d" % int(percent))

    def do_highlight(self, range_, seconds=DEFAULT_HIGHLIGHT, fast=False):
        """Select `range_` for a moment, then restore the previous selection."""
        self._activate_for(range_)
        self._ensure_visible(parse_range(range_)[1])
        hold = 0.0 if fast else float(seconds)
        self._run("set prev to get address of selection\n"
                  "select %s\n" % self._range_expr(range_)
                  + "delay %.2f\n" % hold
                  + "select range prev of active sheet")
