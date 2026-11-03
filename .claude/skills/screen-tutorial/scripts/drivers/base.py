"""Driver interface shared by every app the tutorial pipeline can drive.

Implements the **Actions** table of `references/script-format.md`: the action
vocabulary (`ACTIONS`), how long each action takes on screen (`estimate_seconds`),
and the cell-reference grammar ("B6", "Savings!B6", "A2:B9", "A:A").

A concrete driver (see `excel.py`) subclasses `Driver` and implements one
method per action, plus the lifecycle methods `launch`, `stage`,
`window_title`, `read_value`, `read_text` and `teardown`. The runner in
`tutorial.py` never talks to an app directly; it calls `Driver.perform()`.

`wait` and `at` are timing actions: the runner handles them, not the driver.
"""

import re

# ---------------------------------------------------------------------------
# Action vocabulary (script-format.md § Actions)
# ---------------------------------------------------------------------------
# For each `do` value: required fields, optional fields, and fields of which
# exactly one must be present ("one_of").
ACTIONS = {
    "sheet":        {"required": ["name"], "optional": []},
    "rename_sheet": {"required": ["from", "to"], "optional": []},
    "select":       {"required": [], "optional": [], "one_of": ["cell", "range"]},
    "type":         {"required": ["cell", "text"], "optional": ["pace", "commit"]},
    "set":          {"required": [], "optional": [], "one_of": ["cell", "range"],
                     "one_of_2": ["value", "formula"]},
    "fill_down":    {"required": ["range", "from"], "optional": []},
    "format":       {"required": ["range"], "optional": ["number", "bold", "width", "align"]},
    "header_row":   {"required": ["row", "values"], "optional": ["bold"]},
    "chart":        {"required": ["type", "series"],
                     "optional": ["x", "title", "x_title", "y_title", "at", "size", "y_min"]},
    "scroll":       {"required": ["cell"], "optional": []},
    "zoom":         {"required": ["percent"], "optional": []},
    "wait":         {"required": ["seconds"], "optional": []},
    "at":           {"required": ["fraction"], "optional": []},
    "highlight":    {"required": ["range"], "optional": ["seconds"]},
}

TIMING_ACTIONS = {"wait", "at"}      # handled by the runner
DEFAULT_PACE = 0.045                 # s per character for `type`
DEFAULT_HIGHLIGHT = 1.2              # s for `highlight`
CHART_TYPES = {"line", "column"}
ALIGNMENTS = {"left", "center", "right"}

# Rough on-screen cost of one AppleScript round trip (osascript start-up +
# Excel's reply). Measured ~0.15-0.3 s on the school MacBook Air.
ROUND_TRIP = 0.25


def estimate_seconds(action):
    """Approximate seconds an action keeps the screen busy (for planning).

    Used by `validate`/`dryrun` to predict scene length and by the timing
    model to decide whether actions or narration set a scene's duration.
    `at` returns 0 here; its effect depends on the narration length and is
    handled by `tutorial.plan_scene`.
    """
    do = action.get("do")
    if do == "type":
        pace = float(action.get("pace", DEFAULT_PACE))
        return ROUND_TRIP + 0.15 + len(str(action.get("text", ""))) * pace
    if do == "wait":
        return float(action.get("seconds", 0))
    if do == "highlight":
        return ROUND_TRIP + float(action.get("seconds", DEFAULT_HIGHLIGHT))
    if do == "at":
        return 0.0
    if do == "chart":
        return ROUND_TRIP * 4
    if do == "header_row":
        return ROUND_TRIP + 0.1 * len(action.get("values", []))
    return ROUND_TRIP


# ---------------------------------------------------------------------------
# Cell references (script-format.md § Actions: "B6 or Sheet!B6")
# ---------------------------------------------------------------------------
_CELL = r"\$?([A-Za-z]{1,3})\$?(\d+)"
_REF_RE = re.compile(r"^(?:(?P<sheet>'[^']+'|[^!:]+)!)?(?P<body>.+)$")
_CELL_RE = re.compile(r"^" + _CELL + r"$")
_RANGE_RE = re.compile(r"^" + _CELL + r":" + _CELL + r"$")
_COLS_RE = re.compile(r"^\$?([A-Za-z]{1,3}):\$?([A-Za-z]{1,3})$")
_ROWS_RE = re.compile(r"^\$?(\d+):\$?(\d+)$")


def col_to_num(col):
    """'A' -> 1, 'Z' -> 26, 'AA' -> 27."""
    n = 0
    for ch in col.upper():
        if not "A" <= ch <= "Z":
            raise ValueError("bad column letters: %r" % col)
        n = n * 26 + (ord(ch) - 64)
    return n


def num_to_col(n):
    """1 -> 'A', 27 -> 'AA'."""
    if n < 1:
        raise ValueError("column number must be >= 1")
    letters = ""
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def split_sheet(ref):
    """'Savings!B6' -> ('Savings', 'B6'); 'B6' -> (None, 'B6').
    Quoted sheet names ('My Sheet'!A1) are unquoted."""
    m = _REF_RE.match(ref.strip())
    if not m:
        raise ValueError("bad reference: %r" % ref)
    sheet = m.group("sheet")
    if sheet and sheet.startswith("'"):
        sheet = sheet[1:-1]
    return sheet, m.group("body").replace("$", "").upper()


def parse_range(ref):
    """Parse a cell, range, whole-column or whole-row reference.

    Returns (sheet, (col1, row1, col2, row2)); whole columns use rows 1..None
    and whole rows use columns 1..None. Raises ValueError on bad syntax.
        parse_range("Savings!A2:B9") -> ("Savings", (1, 2, 2, 9))
        parse_range("B6")            -> (None, (2, 6, 2, 6))
        parse_range("A:A")           -> (None, (1, 1, 1, None))
    """
    sheet, body = split_sheet(ref)
    m = _CELL_RE.match(body)
    if m:
        c, r = col_to_num(m.group(1)), int(m.group(2))
        return sheet, (c, r, c, r)
    m = _RANGE_RE.match(body)
    if m:
        c1, r1 = col_to_num(m.group(1)), int(m.group(2))
        c2, r2 = col_to_num(m.group(3)), int(m.group(4))
        return sheet, (min(c1, c2), min(r1, r2), max(c1, c2), max(r1, r2))
    m = _COLS_RE.match(body)
    if m:
        c1, c2 = sorted((col_to_num(m.group(1)), col_to_num(m.group(2))))
        return sheet, (c1, 1, c2, None)
    m = _ROWS_RE.match(body)
    if m:
        r1, r2 = sorted((int(m.group(1)), int(m.group(2))))
        return sheet, (1, r1, None, r2)
    raise ValueError("bad cell or range reference: %r" % ref)


def parse_cell(ref):
    """Like parse_range but insists on one cell: returns (sheet, col, row)."""
    sheet, (c1, r1, c2, r2) = parse_range(ref)
    if (c1, r1) != (c2, r2):
        raise ValueError("expected a single cell, got %r" % ref)
    return sheet, c1, r1


def range_address(box):
    """(1, 2, 2, 9) -> 'A2:B9'; single cells collapse to 'B6'."""
    c1, r1, c2, r2 = box
    if r2 is None:
        return "%s:%s" % (num_to_col(c1), num_to_col(c2))
    if c2 is None:
        return "%d:%d" % (r1, r2)
    a = "%s%d" % (num_to_col(c1), r1)
    b = "%s%d" % (num_to_col(c2), r2)
    return a if a == b else a + ":" + b


def shift_range(ref, rows):
    """Move a range down by `rows` rows (used to expand fill_down sources)."""
    sheet, (c1, r1, c2, r2) = parse_range(ref)
    body = range_address((c1, r1 + rows, c2, r2 + rows))
    return "%s!%s" % (sheet, body) if sheet else body


def is_valid_ref(ref):
    try:
        parse_range(ref)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


# ---------------------------------------------------------------------------
# The abstract driver
# ---------------------------------------------------------------------------
class DriverError(RuntimeError):
    """An app refused an action. The message says which action and why."""


class Driver:
    """One app session. Subclasses implement the `do_*` methods.

    Lifecycle (called by tutorial.py):
        launch()             start / connect to the app, wait until scriptable
        stage(window, stage) new document, worksheets, window size and zoom
        window_title()       substring OpenScreen uses to find the window
        perform(action, fast=False)   one action from the script
        read_value(ref) / read_text(ref)   for checks
        teardown(keep_open=False)   close the document without saving

    `fast=True` means "same end state, no animation" (used to fast-forward
    earlier chapters and by `dryrun --fast`).
    """

    name = "base"

    def __init__(self, log=print):
        self.log = log

    # -- lifecycle --------------------------------------------------------
    def launch(self):
        raise NotImplementedError

    def stage(self, window, stage):
        raise NotImplementedError

    def window_title(self):
        raise NotImplementedError

    def window_size(self):
        """(width, height) of the staged window in points, if known."""
        return None

    def visible_box(self):
        """(col1, row1, col2, row2) currently visible, if the app can say."""
        return None

    def ensure_visible(self, ref):
        """Scroll so the range is on screen (no-op if the app can't)."""
        return None

    def range_rect(self, ref):
        """(left, top, width, height) of a range in window-relative fractions
        0..1, if the app can say. Used to aim OpenScreen camera zooms."""
        return None

    def read_value(self, ref):
        raise NotImplementedError

    def read_text(self, ref):
        raise NotImplementedError

    def teardown(self, keep_open=False):
        raise NotImplementedError

    # -- dispatch -----------------------------------------------------------
    def perform(self, action, fast=False):
        do = action.get("do")
        if do in TIMING_ACTIONS:
            raise DriverError("%r is a timing action; the runner handles it" % do)
        method = getattr(self, "do_" + str(do), None)
        if method is None:
            raise DriverError("%s driver does not support do=%r" % (self.name, do))
        fields = {k: v for k, v in action.items() if k != "do"}
        # Python keywords / builtins used as field names in the script format.
        if "from" in fields:
            fields["from_"] = fields.pop("from")
        if "range" in fields:
            fields["range_"] = fields.pop("range")
        if "type" in fields:
            fields["type_"] = fields.pop("type")
        try:
            return method(fast=fast, **fields)
        except DriverError:
            raise
        except TypeError as err:
            raise DriverError("bad fields for do=%r: %s" % (do, err))

    # -- actions (override in subclasses) ---------------------------------
    def do_sheet(self, name, fast=False):
        raise NotImplementedError

    def do_rename_sheet(self, from_, to, fast=False):
        raise NotImplementedError

    def do_select(self, cell=None, range_=None, fast=False):
        raise NotImplementedError

    def do_type(self, cell, text, pace=DEFAULT_PACE, commit="enter", fast=False):
        raise NotImplementedError

    def do_set(self, cell=None, range_=None, value=None, formula=None, fast=False):
        raise NotImplementedError

    def do_fill_down(self, range_, from_, fast=False):
        raise NotImplementedError

    def do_format(self, range_, number=None, bold=None, width=None, align=None, fast=False):
        raise NotImplementedError

    def do_header_row(self, row, values, bold=True, fast=False):
        raise NotImplementedError

    def do_chart(self, type_, series, x=None, title=None, x_title=None, y_title=None,
                 at=None, size=None, y_min=None, fast=False):
        raise NotImplementedError

    def do_scroll(self, cell, fast=False):
        raise NotImplementedError

    def do_zoom(self, percent, fast=False):
        raise NotImplementedError

    def do_highlight(self, range_, seconds=DEFAULT_HIGHLIGHT, fast=False):
        raise NotImplementedError
