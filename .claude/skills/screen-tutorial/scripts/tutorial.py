#!/usr/bin/env python3
"""Screen-tutorial builder: a JSON script in, a narrated, captioned MP4 out.

    tutorial.py validate <script.tutorial.json>
    tutorial.py dryrun   <script> [--voice draft|say|eleven] [--live] [--keep-open]
                                  [--chapter ID | --part ID | --all-parts]
    tutorial.py build    <script> [--voice draft|say|eleven] [--out DIR]
                                  [--chapter ID | --part ID | --all-parts]
                                  [--no-check] [--no-zoom] [--no-steps] [--quality medium|good|source]
                                  [--fps 30|60] [--play] [--keep-open]

The script format and the timing model are defined in
`references/script-format.md`; each function below names the section it
implements. In short, `build`:

  1. synthesizes every scene's narration first (cached by content hash), so
     every duration is known before recording starts;            (§ Timing model 1)
  2. stages the app, starts an OpenScreen window recording and takes `t0`
     from the recorder's "Recording started" line;                (§ Timing model 2)
  3. for each scene logs start/end relative to t0, runs the actions
     (`at` waits for a fraction of the narration), runs the checks, then
     waits out the rest of the clip plus a 0.6 s breath;          (§ Scene, § Actions)
  4. assembles one narration WAV with each clip at its scene's start and
     exports with `--audio track.wav --audio-mode replace`;      (§ Timing model 3)
  5. writes the SRT from the same timings, optional camera zooms and
     callouts into the OpenScreen project, `.checks.json`, contact sheets
     and `build.log` with the scene timing table.                (§ Timing model 4-5)

Python 3.9 stdlib only. Sibling modules: narration.py (voice), audio.py
(WAV assembly), srt.py (captions), openscreen.py (recorder), drivers/ (apps).
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from drivers import base as drv  # noqa: E402

REPO = HERE.parents[3]                     # .../.claude/skills/screen-tutorial/scripts -> repo
DEFAULT_OUT_ROOT = REPO / "videos" / "tutorials" / "out"
CACHE_DIR = REPO / "videos" / "tutorials" / "narration_cache"

BREATH = 0.6          # s of quiet after each scene (§ Timing model 2)
LEAD_IN = 1.0         # s of still picture before the first scene
TAIL = 1.2            # s of still picture after the last scene
WORDS_PER_SECOND = 2.9
VOICE_MODES = ("draft", "say", "eleven")
APPS = ("excel", "sheets")
CODE_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Za-z0-9]+)*$")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
COMMITS = ("enter", "tab", "none")


# ===========================================================================
# Validation (script-format.md § Top level, § Scene, § Actions)
# ===========================================================================
def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_ref(errors, where, ref, single=False):
    if not isinstance(ref, str) or not drv.is_valid_ref(ref):
        errors.append("%s: bad cell/range reference %r" % (where, ref))
        return
    if single:
        try:
            drv.parse_cell(ref)
        except ValueError:
            errors.append("%s: expected one cell, got %r" % (where, ref))


def validate_action(action, where):
    """Errors for one action object (list of strings; empty = valid)."""
    errors = []
    if not isinstance(action, dict) or "do" not in action:
        return ["%s: an action must be an object with a `do` key" % where]
    do = action["do"]
    spec = drv.ACTIONS.get(do)
    if spec is None:
        return ["%s: unknown action do=%r (known: %s)" % (where, do, ", ".join(sorted(drv.ACTIONS)))]
    where = "%s (%s)" % (where, do)
    allowed = set(spec["required"]) | set(spec["optional"]) | set(spec.get("one_of", [])) \
        | set(spec.get("one_of_2", [])) | {"do"}
    for key in spec["required"]:
        if key not in action:
            errors.append("%s: missing `%s`" % (where, key))
    for group in ("one_of", "one_of_2"):
        if group in spec and sum(k in action for k in spec[group]) != 1:
            errors.append("%s: needs exactly one of %s" % (where, " / ".join(spec[group])))
    for key in action:
        if key not in allowed:
            errors.append("%s: unknown field `%s`" % (where, key))
    if errors:
        return errors

    if do in ("sheet",):
        if not isinstance(action["name"], str) or not action["name"].strip():
            errors.append("%s: `name` must be a sheet name" % where)
    elif do == "rename_sheet":
        for k in ("from", "to"):
            if not isinstance(action[k], str) or not action[k].strip():
                errors.append("%s: `%s` must be a sheet name" % (where, k))
    elif do in ("select", "highlight", "format", "fill_down"):
        for k in ("cell", "range", "from"):
            if k in action:
                _check_ref(errors, where, action[k], single=(k == "cell"))
    elif do == "type":
        _check_ref(errors, where, action["cell"], single=True)
        if not isinstance(action["text"], (str, int, float)) or str(action["text"]) == "":
            errors.append("%s: `text` must be non-empty" % where)
        if "pace" in action and (not _num(action["pace"]) or not 0 <= action["pace"] <= 1):
            errors.append("%s: `pace` must be seconds per character (0-1)" % where)
        if action.get("commit", "enter") not in COMMITS:
            errors.append("%s: `commit` must be one of %s" % (where, ", ".join(COMMITS)))
    elif do == "set":
        _check_ref(errors, where, action.get("cell") or action.get("range"), single="cell" in action)
        if "formula" in action and not str(action["formula"]).startswith("="):
            errors.append("%s: `formula` should start with '='" % where)
    elif do == "header_row":
        if not isinstance(action["row"], int) or action["row"] < 1:
            errors.append("%s: `row` must be a row number" % where)
        if not isinstance(action["values"], list) or not action["values"]:
            errors.append("%s: `values` must be a non-empty list" % where)
    elif do == "chart":
        if action["type"] not in drv.CHART_TYPES:
            errors.append("%s: `type` must be line or column" % where)
        if not isinstance(action["series"], list) or not action["series"]:
            errors.append("%s: `series` must be a non-empty list of {range, name}" % where)
        else:
            for i, s in enumerate(action["series"]):
                if not isinstance(s, dict) or "range" not in s:
                    errors.append("%s: series %d needs a `range`" % (where, i + 1))
                else:
                    _check_ref(errors, where, s["range"])
        for k in ("x",):
            if k in action:
                _check_ref(errors, where, action[k])
        if "at" in action:
            _check_ref(errors, where, action["at"], single=True)
        if "size" in action and not (isinstance(action["size"], list) and len(action["size"]) == 2
                                     and all(_num(v) and v > 0 for v in action["size"])):
            errors.append("%s: `size` must be [width, height]" % where)
    elif do == "scroll":
        _check_ref(errors, where, action["cell"], single=True)
    elif do == "zoom":
        if not _num(action["percent"]) or not 10 <= action["percent"] <= 400:
            errors.append("%s: `percent` must be 10-400" % where)
    elif do == "wait":
        if not _num(action["seconds"]) or action["seconds"] < 0:
            errors.append("%s: `seconds` must be >= 0" % where)
    elif do == "at":
        if not _num(action["fraction"]) or not 0 <= action["fraction"] <= 1:
            errors.append("%s: `fraction` must be 0-1" % where)
    if do == "highlight" and "seconds" in action and (not _num(action["seconds"]) or action["seconds"] < 0):
        errors.append("%s: `seconds` must be >= 0" % where)
    if do == "format" and "align" in action and action["align"] not in drv.ALIGNMENTS:
        errors.append("%s: `align` must be left, center or right" % where)
    return errors


def _validate_scene(scene, where, known_sheets, errors, warnings):
    """Validate one scene (also a part's intro/outro). Appends to errors /
    warnings, adds sheets it creates to known_sheets, returns its id or None."""
    if not isinstance(scene, dict):
        errors.append("%s: must be an object" % where)
        return None
    sid = scene.get("id")
    if not isinstance(sid, str) or not ID_RE.match(sid):
        errors.append("%s: `id` must be kebab-case" % where)
        sid = None
    else:
        where = "scene %r" % sid
    say = scene.get("say")
    if not isinstance(say, str) or not say.strip():
        errors.append("%s: `say` is required" % where)
    else:
        words = len(say.split())
        if words > 45:
            warnings.append("%s: %d words; keep scenes under 45 words" % (where, words))
        if re.search(r"[=%$^*/+<>]|\d", say):
            warnings.append("%s: `say` contains digits or symbols; write words "
                            "(\"four point five percent\") — the voice reads it literally" % where)
    if "caption" in scene and not isinstance(scene["caption"], str):
        errors.append("%s: `caption` must be text" % where)
    if "voice_direction" in scene and not isinstance(scene["voice_direction"], str):
        errors.append("%s: `voice_direction` must be text (\"\" = none)" % where)
    actions = scene.get("actions", [])
    if not isinstance(actions, list):
        errors.append("%s: `actions` must be a list" % where)
        actions = []
    last_fraction = 0.0
    for j, action in enumerate(actions, start=1):
        errors += validate_action(action, "%s action %d" % (where, j))
        if not isinstance(action, dict):
            continue
        if action.get("do") == "at" and _num(action.get("fraction")):
            if action["fraction"] < last_fraction:
                warnings.append("%s action %d: `at` %.2f is earlier than a previous `at` "
                                "(it will not wait)" % (where, j, action["fraction"]))
            last_fraction = max(last_fraction, action["fraction"])
        if action.get("do") == "sheet":
            known_sheets.add(action.get("name"))
        if action.get("do") == "rename_sheet":
            known_sheets.add(action.get("to"))
        for k in ("cell", "range", "from", "at", "x"):
            ref = action.get(k)
            if isinstance(ref, str) and "!" in ref and drv.is_valid_ref(ref):
                sheet = drv.split_sheet(ref)[0]
                if sheet not in known_sheets:
                    warnings.append("%s action %d: sheet %r is not in stage.sheets "
                                    "or created earlier" % (where, j, sheet))
    if "zoom" in scene:
        _check_ref(errors, where + " zoom", scene["zoom"])
    for j, check in enumerate(scene.get("checks", []) or [], start=1):
        cw = "%s check %d" % (where, j)
        if not isinstance(check, dict) or "cell" not in check:
            errors.append("%s: needs `cell`" % cw)
            continue
        _check_ref(errors, cw, check["cell"], single=True)
        if ("equals" in check) == ("text" in check):
            errors.append("%s: needs exactly one of `equals` / `text`" % cw)
        if "equals" in check and not _num(check["equals"]):
            errors.append("%s: `equals` must be a number" % cw)
        if "tol" in check and (not _num(check["tol"]) or check["tol"] < 0):
            errors.append("%s: `tol` must be >= 0" % cw)
    callout = scene.get("callout")
    if callout is not None:
        if not isinstance(callout, dict) or not isinstance(callout.get("text"), str):
            errors.append("%s: `callout` needs `text`" % where)
        elif "at" in callout and (not _num(callout["at"]) or not 0 <= callout["at"] < 1):
            errors.append("%s: `callout.at` must be 0-1" % where)

    return sid


def validate_script(script):
    """Return (errors, warnings) for a whole script. Errors block a build."""
    errors, warnings = [], []
    if not isinstance(script, dict):
        return ["the script must be a JSON object"], []

    code = script.get("code")
    if not isinstance(code, str) or not CODE_RE.match(code):
        errors.append("code: must look like CSM-U2-hysa-car-sheets (upper-case prefix, hyphenated)")
    if not isinstance(script.get("title"), str) or not script["title"].strip():
        errors.append("title: required")
    if script.get("app") not in APPS:
        errors.append("app: must be one of %s" % ", ".join(APPS))
    window = script.get("window", {})
    if not isinstance(window, dict) or not all(_num(window.get(k, 1)) and window.get(k, 1) > 0
                                               for k in ("width", "height")):
        errors.append("window: needs positive width and height")
    stage = script.get("stage", {})
    if not isinstance(stage, dict):
        errors.append("stage: must be an object")
        stage = {}
    if "zoom" in stage and (not _num(stage["zoom"]) or not 10 <= stage["zoom"] <= 400):
        errors.append("stage.zoom: must be 10-400")
    sheets = stage.get("sheets", [])
    if not isinstance(sheets, list) or not all(isinstance(s, str) and s for s in sheets):
        errors.append("stage.sheets: must be a list of names")
        sheets = []
    elif len(set(sheets)) != len(sheets):
        errors.append("stage.sheets: names must be unique")
    voice = script.get("voice", {})
    if voice and (not isinstance(voice, dict) or voice.get("mode", "draft") not in VOICE_MODES):
        errors.append("voice.mode: must be one of %s" % ", ".join(VOICE_MODES))
    if isinstance(voice, dict) and "direction" in voice and not isinstance(voice["direction"], str):
        errors.append("voice.direction: must be text, e.g. \"[dry, wry, understated]\"")

    scenes = script.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes: must be a non-empty list")
        return errors, warnings

    ids = []
    known_sheets = set(sheets)
    for i, scene in enumerate(scenes, start=1):
        sid = _validate_scene(scene, "scene %d" % i, known_sheets, errors, warnings)
        if sid is not None:
            if sid in ids:
                errors.append("scene %r: duplicate id" % sid)
            ids.append(sid)

    seen = {}
    for chapter in script.get("chapters", []) or []:
        cid = chapter.get("id") if isinstance(chapter, dict) else None
        if not isinstance(cid, str) or not ID_RE.match(cid):
            errors.append("chapters: every chapter needs a kebab-case `id`")
            continue
        for sid in chapter.get("scenes", []):
            if sid not in ids:
                errors.append("chapter %r: unknown scene %r" % (cid, sid))
            elif sid in seen:
                errors.append("chapter %r: scene %r is already in chapter %r" % (cid, sid, seen[sid]))
            seen[sid] = cid
    _validate_parts(script, ids, known_sheets, errors, warnings)
    return errors, warnings


def _validate_parts(script, scene_ids, known_sheets, errors, warnings):
    """§ Parts: kebab-case unique ids, known chapters, each chapter in at most
    one part, intro/outro valid scenes whose ids collide with nothing."""
    parts = script.get("parts")
    if parts is None:
        return
    if not isinstance(parts, list):
        errors.append("parts: must be a list")
        return
    chapters = {c.get("id"): c for c in script.get("chapters", []) or [] if isinstance(c, dict)}
    part_ids, owner, extra_ids = [], {}, set()
    for i, part in enumerate(parts, start=1):
        where = "part %d" % i
        if not isinstance(part, dict):
            errors.append("%s: must be an object" % where)
            continue
        pid = part.get("id")
        if not isinstance(pid, str) or not ID_RE.match(pid):
            errors.append("%s: `id` must be kebab-case" % where)
        else:
            where = "part %r" % pid
            if pid in part_ids:
                errors.append("%s: duplicate id" % where)
            part_ids.append(pid)
        if "title" in part and (not isinstance(part["title"], str) or not part["title"].strip()):
            errors.append("%s: `title` must be text" % where)
        unknown = set(part) - {"id", "title", "chapters", "intro", "outro"}
        if unknown:
            errors.append("%s: unknown field(s) %s" % (where, ", ".join(sorted(unknown))))
        chs = part.get("chapters")
        if not isinstance(chs, list) or not chs:
            errors.append("%s: `chapters` must be a non-empty list of chapter ids" % where)
            chs = []
        for cid in chs:
            if cid not in chapters:
                errors.append("%s: unknown chapter %r" % (where, cid))
            elif cid in owner:
                errors.append("%s: chapter %r is already in part %r" % (where, cid, owner[cid]))
            else:
                owner[cid] = pid
        for slot in ("intro", "outro"):
            if slot not in part:
                continue
            sid = _validate_scene(part[slot], "%s %s" % (where, slot), set(known_sheets),
                                  errors, warnings)
            if sid is None:
                continue
            if sid in scene_ids or sid in extra_ids:
                errors.append("%s %s: id %r collides with another scene" % (where, slot, sid))
            extra_ids.add(sid)
    for pid in part_ids:
        try:
            before, selected, _ = part_scenes(script, pid)
        except (SystemExit, KeyError, ValueError, TypeError):
            continue
        if not selected:
            continue
        order = [s["id"] for s in script["scenes"]]
        first, last = order.index(selected[0]["id"]), order.index(selected[-1]["id"])
        chosen = {s["id"] for s in selected}
        gaps = [sid for sid in order[first:last + 1] if sid not in chosen]
        if gaps:
            warnings.append("part %r: scenes %s sit between its chapters and are not run "
                            "in its recording" % (pid, ", ".join(gaps[:5])))


def load_script(path):
    try:
        return json.loads(Path(path).read_text())
    except ValueError as err:
        raise SystemExit("%s: not valid JSON: %s" % (path, err))


# ===========================================================================
# Timing (script-format.md § Scene: "duration is max(narration, actions) + breath")
# ===========================================================================
def estimate_narration(text):
    """Draft-mode estimate, same rule as the Manim engine (2.9 words/s)."""
    return max(1.5, len(text.split()) / WORDS_PER_SECOND)


def plan_scene(narration_s, actions, breath=BREATH):
    """Predict a scene's timing before it runs.

    Walks the actions with a clock: `at` jumps the clock forward to that
    fraction of the narration (never back), everything else adds its
    estimated cost. Returns {"actions": seconds the actions need,
    "duration": max(narration, actions) + breath}.
    """
    t = 0.0
    for action in actions:
        if action.get("do") == "at":
            t = max(t, float(action["fraction"]) * narration_s)
        else:
            t += drv.estimate_seconds(action)
    return {"actions": t, "duration": max(narration_s, t) + breath}


def chapter_scenes(script, chapter_id):
    """(before, selected, after) scene lists for --chapter (§ Top level: chapters)."""
    scenes = script["scenes"]
    if not chapter_id:
        return [], scenes, []
    chapter = next((c for c in script.get("chapters", []) if c.get("id") == chapter_id), None)
    if chapter is None:
        raise SystemExit("no chapter %r (have: %s)" % (
            chapter_id, ", ".join(c.get("id", "?") for c in script.get("chapters", [])) or "none"))
    wanted = set(chapter["scenes"])
    idx = [i for i, s in enumerate(scenes) if s["id"] in wanted]
    first, last = min(idx), max(idx)
    return scenes[:first], [s for s in scenes[first:last + 1] if s["id"] in wanted], scenes[last + 1:]


def find_part(script, part_id):
    part = next((p for p in script.get("parts", []) or [] if p.get("id") == part_id), None)
    if part is None:
        raise SystemExit("no part %r (have: %s)" % (
            part_id, ", ".join(p.get("id", "?") for p in script.get("parts", []) or []) or "none"))
    return part


def part_scenes(script, part_id):
    """(before, selected, after) for --part (§ Parts). `before` is every script
    scene ahead of the part's first scene, so fast-forwarding it rebuilds the
    workbook exactly; `selected` is the part's chapter scenes in script order,
    without the part's intro/outro (see recorded_scenes)."""
    part = find_part(script, part_id)
    chapters = {c["id"]: c for c in script.get("chapters", []) or []}
    wanted = set()
    for cid in part["chapters"]:
        if cid not in chapters:
            raise SystemExit("part %r: unknown chapter %r" % (part_id, cid))
        wanted.update(chapters[cid]["scenes"])
    scenes = script["scenes"]
    idx = [i for i, s in enumerate(scenes) if s["id"] in wanted]
    if not idx:
        return scenes, [], []
    first, last = min(idx), max(idx)
    return scenes[:first], [s for s in scenes[first:last + 1] if s["id"] in wanted], scenes[last + 1:]


def recorded_scenes(script, part_id, selected):
    """[intro] + selected + [outro] for one part (§ Parts)."""
    part = find_part(script, part_id)
    return ([part["intro"]] if part.get("intro") else []) + list(selected) + \
        ([part["outro"]] if part.get("outro") else [])


def select_scenes(script, chapter=None, part=None):
    """(before, recorded, name) for a build/dryrun run. Plain runs record every
    script scene and never a part intro/outro."""
    if chapter and part:
        raise SystemExit("use --chapter or --part, not both")
    if part:
        before, selected, _ = part_scenes(script, part)
        return before, recorded_scenes(script, part, selected), script["code"] + "-" + part
    before, selected, _ = chapter_scenes(script, chapter)
    return before, selected, script["code"] + ("-" + chapter if chapter else "")


# ===========================================================================
# Step captions (script-format.md § Step captions): a burned-in lower third
# naming the action on screen, so students can follow along.
# ===========================================================================
STEP_ACTIONS = ("type", "set", "fill_down", "format", "header_row", "chart", "sheet",
                "rename_sheet", "zoom")
STEP_MAX_CHARS = 60           # merge / truncation budget
STEP_BOX = {"cx": 50, "cy": 93, "width": 76, "height": 7}   # % of the frame; centre point
STEP_FONT_MAX = 36            # px at 1080p: a 60-char formula fits the box
STEP_FONT_MIN = 24
STEP_CHAR_EM = 0.6            # IBM Plex Mono advance width / font size
STEP_STYLE = {
    "color": "#f5f5f4",
    "backgroundColor": "#111111",
    "fontFamily": "IBM Plex Mono",
    "fontWeight": "normal",
    "textAlign": "center",
    "textAnimation": "fade",
}
CALLOUT_Y_WITH_STEPS = 78     # callout box top (its 9% height ends above the step bar)


def display_ref(ref, active):
    """A reference as the student types it: drop `Sheet!` on the active sheet."""
    ref = str(ref)
    if "!" not in ref:
        return ref
    try:
        sheet, local = drv.split_sheet(ref)
    except ValueError:
        return ref
    return local if sheet == active else ref


def _ref_sheet(ref):
    if isinstance(ref, str) and "!" in ref:
        try:
            return drv.split_sheet(ref)[0]
        except ValueError:
            return None
    return None


def _columns(ref):
    """Column label of a range: "E", "B:F"."""
    try:
        _, (c1, _, c2, _) = drv.parse_range(ref)
    except ValueError:
        return str(ref)
    c2 = c2 or c1
    return drv.num_to_col(c1) if c1 == c2 else "%s:%s" % (drv.num_to_col(c1), drv.num_to_col(c2))


def _fit(text, limit=STEP_MAX_CHARS):
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def step_text(action, active=None):
    """Lower-third text for one action, or None if it gets no caption."""
    do = action.get("do")
    ref = lambda k: display_ref(action[k], active)  # noqa: E731
    if do == "type":
        return "%s ← %s" % (ref("cell"), action["text"])
    if do == "set":
        target = ref("cell") if "cell" in action else ref("range")
        value = action["formula"] if "formula" in action else action.get("value")
        return "%s ← %s" % (target, value)
    if do == "fill_down":
        return "Fill down %s → %s  (⌘D)" % (ref("from"), ref("range"))
    if do == "format":
        target = ref("range")
        parts = []
        if "number" in action:
            parts.append(str(action["number"]))
        if "bold" in action:
            parts.append("bold" if action["bold"] else "not bold")
        if "align" in action:
            parts.append("align " + str(action["align"]))
        if "width" in action:
            parts.append("width %s" % action["width"])
        if not parts:
            return None
        if len(parts) > 1:
            return _fit("Format %s: %s" % (target, ", ".join(parts)))
        if "number" in action:
            return _fit("Format %s as %s" % (target, action["number"]))
        if "bold" in action:
            return "%s %s" % ("Bold" if action["bold"] else "Unbold", target)
        if "align" in action:
            return "Align %s %s" % (target, action["align"])
        return "Width %s: %s" % (_columns(action["range"]), action["width"])
    if do == "header_row":
        head = "Row %d headers: " % action["row"]
        values = [str(v) for v in action["values"]]
        text = head + " · ".join(values)
        if len(text) <= STEP_MAX_CHARS:
            return text
        shown = []
        for v in values:
            if len(head + " · ".join(shown + [v]) + " · …") > STEP_MAX_CHARS:
                break
            shown.append(v)
        return head + " · ".join(shown + ["…"])
    if do == "chart":
        base = "Insert %s chart" % action["type"]
        return _fit(base + (": " + action["title"] if action.get("title") else ""))
    if do == "sheet":
        return "Sheet: %s" % action["name"]
    if do == "rename_sheet":
        return "Rename sheet %s → %s" % (action["from"], action["to"])
    if do == "zoom":
        return "Zoom %s%%" % action["percent"]
    return None


def next_active(action, active):
    """The active sheet after an action (drivers activate a qualified ref's sheet)."""
    do = action.get("do")
    if do == "sheet":
        return action["name"]
    if do == "rename_sheet":
        return action["to"] if action["from"] == active else active
    for k in ("cell", "range", "from"):
        sheet = _ref_sheet(action.get(k))
        if sheet:
            return sheet
    return active


def initial_active(script, before=()):
    """Active sheet at the start of the recording: the first staged sheet,
    then whatever the fast-forwarded scenes switched to."""
    sheets = (script.get("stage") or {}).get("sheets") or []
    active = sheets[0] if sheets else None
    for scene in before:
        for action in scene.get("actions", []):
            active = next_active(action, active)
    return active


def scene_steps(scene, active=None):
    """[(action_index, text)] for a scene, plus the active sheet afterwards.
    Consecutive `type`/`set` captions merge while the line stays ≤ 60 chars;
    `at`/`wait` between them do not break the run, any other action does."""
    steps = []
    prev_assign = False
    for i, action in enumerate(scene.get("actions", [])):
        if action.get("do") in drv.TIMING_ACTIONS:
            continue
        text = step_text(action, active)
        active = next_active(action, active)
        if text is None:
            prev_assign = False
            continue
        text = _fit(text)
        assign = action.get("do") in ("type", "set")
        if assign and prev_assign and steps:
            merged = steps[-1][1] + "   " + text
            if len(merged) <= STEP_MAX_CHARS:
                steps[-1] = (steps[-1][0], merged)
                continue
        steps.append((i, text))
        prev_assign = assign
    return steps, active


def step_timings(entry, steps):
    """[{start, end, text}]: each caption runs from its action's start to the
    next caption's start, the last one to the scene's end."""
    out = []
    for n, (index, text) in enumerate(steps):
        start = entry["actions"][index]["start"]
        if n + 1 < len(steps):
            end = entry["actions"][steps[n + 1][0]]["start"]
        else:
            end = entry["end"]
        out.append({"start": start, "end": max(start + 0.3, end), "text": text})
    return out


def step_font_size(text, frame_w=1920):
    """Largest size up to STEP_FONT_MAX whose monospace line fits the box at
    1080p, never below STEP_FONT_MIN."""
    usable = frame_w * STEP_BOX["width"] / 100.0 - 48     # inner padding
    fit = int(usable / (STEP_CHAR_EM * max(1, len(text))))
    return max(STEP_FONT_MIN, min(STEP_FONT_MAX, fit))


def step_regions(timeline, openscreen):
    """OpenScreen text annotations for every scene's steps."""
    x = STEP_BOX["cx"] - STEP_BOX["width"] / 2.0
    y = STEP_BOX["cy"] - STEP_BOX["height"] / 2.0
    notes = []
    for entry in timeline:
        for n, step in enumerate(entry.get("steps", []), start=1):
            style = dict(STEP_STYLE, fontSize=step_font_size(step["text"]))
            notes.append(openscreen.text_annotation(
                "step-%s-%d" % (entry["id"], n), step["start"], step["end"], step["text"],
                x=x, y=y, width=STEP_BOX["width"], height=STEP_BOX["height"],
                style=style, z_index=20))
    return notes


def narration_cues(timeline):
    """SRT cues from scene timings (§ Timing model 4): each scene's caption
    (or spoken text) spans from its start to the end of its clip."""
    return [(s["start"], s["start"] + s["narration"], s["caption"]) for s in timeline]


def zoom_scale_for(rect, fill=0.55, lo=1.25, hi=2.0):
    """Magnification that makes a range fill about `fill` of the frame,
    kept gentle (1.25-2x) so the viewer never loses where they are."""
    _, _, w, h = rect
    need = min(fill / max(w, 1e-3), fill / max(h, 1e-3))
    return max(lo, min(hi, need))


# ===========================================================================
# Checks (script-format.md § Check semantics)
# ===========================================================================
def evaluate_check(check, value=None, text=None):
    """Compare one check; return a result dict (pure, unit-tested)."""
    result = {"cell": check["cell"]}
    if "equals" in check:
        tol = float(check.get("tol", 1e-6))
        result.update(kind="equals", expected=check["equals"], tol=tol, actual=value)
        result["pass"] = _num(value) and abs(float(value) - float(check["equals"])) <= tol
    else:
        result.update(kind="text", expected=check["text"], actual=text)
        result["pass"] = (text or "").strip() == str(check["text"]).strip()
    return result


def run_checks(driver, scene):
    results = []
    for check in scene.get("checks", []) or []:
        try:
            if "equals" in check:
                res = evaluate_check(check, value=driver.read_value(check["cell"]))
            else:
                res = evaluate_check(check, text=driver.read_text(check["cell"]))
        except drv.DriverError as err:
            res = {"cell": check["cell"], "pass": False, "error": str(err)}
        res["scene"] = scene["id"]
        results.append(res)
    return results


def describe_check(res):
    if "error" in res:
        return "%s ERROR %s" % (res["cell"], res["error"])
    if res["kind"] == "equals":
        return "%s = %r (want %r ± %g)" % (res["cell"], res["actual"], res["expected"], res["tol"])
    return "%s shows %r (want %r)" % (res["cell"], res["actual"], res["expected"])


# ===========================================================================
# Running scenes against a driver
# ===========================================================================
class Log:
    """Print and append to build.log."""

    def __init__(self, path=None):
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("")

    def __call__(self, msg=""):
        print(msg, flush=True)
        if self.path:
            with self.path.open("a") as fh:
                fh.write(msg + "\n")


def _sleep_until(clock, target):
    delay = target - clock()
    if delay > 0:
        time.sleep(delay)


def run_scene(driver, scene, narration_s, clock, log, fast=False, clip=None,
              play=False, check=True, measure_zoom=False):
    """Perform one scene in real time (§ Scene, § Actions, § Timing model 2).

    `clock()` returns seconds since t0. Returns the scene's timeline entry:
    start/end, per-action times, check results, and (if asked) the zoom
    target rectangle measured on screen.
    """
    entry = {"id": scene["id"], "narration": narration_s,
             "caption": scene.get("caption") or scene["say"], "actions": []}
    start = clock()
    entry["start"] = start
    player = None
    if play and clip and not fast:
        player = subprocess.Popen(["afplay", str(clip)])
    if scene.get("zoom"):
        try:
            driver.ensure_visible(scene["zoom"])      # § Scene: "keep this range in view"
            if measure_zoom:
                entry["zoom_rect"] = driver.range_rect(scene["zoom"])
        except drv.DriverError as err:
            log("  warning: zoom %s: %s" % (scene["zoom"], err))
    for action in scene.get("actions", []):
        do = action["do"]
        t_a = clock()
        if do == "at":
            if not fast:
                _sleep_until(clock, start + float(action["fraction"]) * narration_s)
        elif do == "wait":
            if not fast:
                time.sleep(float(action["seconds"]))
        else:
            driver.perform(action, fast=fast)
        entry["actions"].append({"do": do, "target": action.get("cell") or action.get("range")
                                 or action.get("name") or "", "start": t_a, "end": clock()})
    entry["actions_end"] = clock()
    entry["checks"] = run_checks(driver, scene) if check else []
    if not fast:
        _sleep_until(clock, max(start + narration_s, entry["actions_end"]) + BREATH)
    entry["end"] = clock()
    if player and player.poll() is None:
        player.terminate()
    return entry


def scene_table(rows, title):
    """Fixed-width table for the terminal and build.log."""
    head = "%-18s %7s %7s %7s %7s %7s  %s" % ("scene", "start", "end", "voice", "actions",
                                             "length", "checks")
    lines = [title, head, "-" * len(head)]
    for r in rows:
        lines.append("%-18s %7s %7s %7.1f %7.1f %7.1f  %s" % (
            r["id"][:18],
            "%.1f" % r["start"] if r.get("start") is not None else "",
            "%.1f" % r["end"] if r.get("end") is not None else "",
            r["narration"], r["actions_s"], r["length"], r.get("checks_label", "")))
    total = sum(r["length"] for r in rows)
    lines.append("-" * len(head))
    whole = int(round(total))
    lines.append("%-18s %47.1f s (%d:%02d)" % ("total", total, whole // 60, whole % 60))
    return "\n".join(lines)


def checks_label(results):
    if not results:
        return "-"
    bad = [r for r in results if not r["pass"]]
    return "PASS %d" % len(results) if not bad else "FAIL %d/%d" % (len(bad), len(results))


# ===========================================================================
# Narration (§ Timing model 1)
# ===========================================================================
def voice_direction(script, scene):
    """The scene's voice direction: its own `voice_direction` ("" = none),
    else the script's `voice.direction`."""
    if "voice_direction" in scene:
        return scene["voice_direction"] or None
    return ((script or {}).get("voice") or {}).get("direction") or None


def synthesize_all(scenes, mode, log, script=None):
    """[(clip_path_or_None, seconds)] for each scene; neighbours as context.
    The voice direction goes to the engine only, never to captions."""
    import narration
    out = []
    for i, scene in enumerate(scenes):
        prev_text = scenes[i - 1]["say"] if i > 0 else None
        next_text = scenes[i + 1]["say"] if i + 1 < len(scenes) else None
        clip, seconds = narration.synthesize(scene["say"], mode, CACHE_DIR,
                                             prev_text=prev_text, next_text=next_text,
                                             direction=voice_direction(script, scene))
        out.append((clip, seconds))
    log("narration: %d clips (%s), %.1f s of speech" % (len(out), mode, sum(s for _, s in out)))
    return out


# ===========================================================================
# Commands
# ===========================================================================
def _plan_rows(scenes):
    rows = []
    for scene in scenes:
        n = estimate_narration(scene["say"])
        plan = plan_scene(n, scene.get("actions", []))
        rows.append({"id": scene["id"], "narration": n, "actions_s": plan["actions"],
                     "length": plan["duration"],
                     "checks_label": "%d" % len(scene.get("checks", []) or [])})
    return rows


def voice_summary(script):
    """Effective narrator: voice id, model, settings, direction."""
    import narration
    voice = script.get("voice") or {}
    lines = ["voice: mode=%s id=%s model=%s" % (voice.get("mode", "draft"),
                                                narration.ELEVEN_VOICE_ID, narration.ELEVEN_MODEL),
             "voice settings: %s" % json.dumps(narration.ELEVEN_SETTINGS, sort_keys=True),
             "voice direction: %s" % (voice.get("direction") or "(none)")]
    overrides = [s["id"] for s in script["scenes"] if "voice_direction" in s]
    if overrides:
        lines.append("voice direction overridden in: %s" % ", ".join(overrides))
    lines += ["warning: " + w for w in narration.SETTINGS_WARNINGS]
    return lines


def cmd_validate(args):
    script = load_script(args.script)
    errors, warnings = validate_script(script)
    for w in warnings:
        print("warning: " + w)
    for e in errors:
        print("ERROR: " + e)
    if errors:
        print("%d error(s); fix them before dryrun/build." % len(errors))
        return 1
    rows = _plan_rows(script["scenes"])
    print(scene_table(rows, "%s — %s (draft estimates; checks not run)" % (script["code"],
                                                                         script["title"])))
    for line in voice_summary(script):
        print(line)
    parts = script.get("parts") or []
    if parts:
        print("parts (draft estimates, intro/outro included):")
        for part in parts:
            _, recorded, name = select_scenes(script, part=part["id"])
            total = sum(r["length"] for r in _plan_rows(recorded)) + LEAD_IN + TAIL
            print("  %-6s %3d scenes  %5.1f min  %s  %s" % (
                part["id"], len(recorded), total / 60.0, name, part.get("title", "")))
        covered = {sid for part in parts for cid in part["chapters"]
                   for c in script.get("chapters", []) if c["id"] == cid for sid in c["scenes"]}
        loose = [s["id"] for s in script["scenes"] if s["id"] not in covered]
        if loose:
            print("  not in any part (plain build only): %s" % ", ".join(loose))
    print("OK: %d scenes valid." % len(rows))
    return 0


def _stage(script, log):
    from drivers import get_driver
    driver = get_driver(script["app"], log=log)
    log("launching %s ..." % script["app"])
    driver.launch()
    driver.stage(script.get("window", {}), script.get("stage", {}))
    log("staged: window %r %s" % (driver.window_title(), driver.window_size()))
    return driver


def _fast_forward(driver, scenes, log):
    """Bring the document to the state at the start of a chapter."""
    if not scenes:
        return
    log("fast-forwarding %d earlier scene(s) ..." % len(scenes))
    for scene in scenes:
        for action in scene.get("actions", []):
            if action["do"] not in drv.TIMING_ACTIONS:
                driver.perform(action, fast=True)


def _runs(script, args):
    """[(part_id_or_None, before, recorded, name)] for this command line."""
    if getattr(args, "all_parts", False):
        if args.chapter or args.part:
            raise SystemExit("--all-parts cannot be combined with --chapter or --part")
        parts = script.get("parts") or []
        if not parts:
            raise SystemExit("--all-parts: the script has no `parts`")
        return [(p["id"],) + select_scenes(script, part=p["id"]) for p in parts]
    part = getattr(args, "part", None)
    return [(part,) + select_scenes(script, chapter=args.chapter, part=part)]


def _run_each(runs, one, log_line=print):
    """Run `one(run)` per run; with several runs, keep going past a failure and
    print a summary table. Returns the exit code."""
    if len(runs) == 1:
        return one(runs[0])["rc"]
    results = []
    for run in runs:
        try:
            res = one(run)
        except (Exception, SystemExit) as err:     # noqa: BLE001 — keep building the next part
            res = {"rc": 1, "error": str(err) or err.__class__.__name__}
        res.setdefault("name", run[3])
        res["part"] = run[0]
        results.append(res)
    log_line("")
    log_line(parts_table(results))
    return 1 if any(r["rc"] for r in results) else 0


def parts_table(results):
    head = "%-8s %9s %-12s %s" % ("part", "duration", "checks", "file")
    lines = ["parts", head, "-" * len(head)]
    for r in results:
        secs = r.get("seconds")
        dur = "%d:%02d" % (int(round(secs)) // 60, int(round(secs)) % 60) if secs else "-"
        status = r.get("checks", "-")
        if r.get("rc") and "error" in r:
            status = "ERROR"
        lines.append("%-8s %9s %-12s %s" % (r["part"], dur, status,
                                            r.get("file") or r.get("error", "")[:60]))
    return "\n".join(lines)


def cmd_dryrun(args):
    """Drive the app and run every check without recording (fast by default)."""
    script = load_script(args.script)
    errors, warnings = validate_script(script)
    if errors:
        for e in errors:
            print("ERROR: " + e)
        return 1
    mode = args.voice or "draft"
    return _run_each(_runs(script, args), lambda run: _dryrun_one(script, args, mode, *run))


def _dryrun_one(script, args, mode, part, before, scenes, name):
    log = Log()
    clips = synthesize_all(scenes, mode, log, script) if mode != "draft" else \
        [(None, estimate_narration(s["say"])) for s in scenes]
    driver = _stage(script, log)
    t0 = time.time()
    clock = lambda: time.time() - t0  # noqa: E731
    rows, all_checks, failed = [], [], False
    try:
        _fast_forward(driver, before, log)
        for scene, (clip, n) in zip(scenes, clips):
            entry = run_scene(driver, scene, n, clock, log, fast=not args.live)
            plan = plan_scene(n, scene.get("actions", []))
            for res in entry["checks"]:
                log("  %s %-10s %s" % ("PASS" if res["pass"] else "FAIL", scene["id"],
                                       describe_check(res)))
            failed = failed or any(not r["pass"] for r in entry["checks"])
            all_checks += entry["checks"]
            rows.append({"id": scene["id"], "narration": n, "actions_s": plan["actions"],
                         "length": plan["duration"], "checks_label": checks_label(entry["checks"]),
                         "start": entry["start"] if args.live else None,
                         "end": entry["end"] if args.live else None})
    finally:
        driver.teardown(keep_open=args.keep_open)
    log(scene_table(rows, "%s — dryrun (%s narration%s)" % (
        name, mode, ", live pacing" if args.live else "; lengths are estimates")))
    log("checks: %s" % ("all %d passed" % len(all_checks) if not failed else "FAILED"))
    return {"rc": 1 if failed else 0, "name": name, "seconds": sum(r["length"] for r in rows),
            "checks": "FAIL" if failed else checks_label(all_checks), "file": "(dryrun)"}


def cmd_build(args):
    """Record, mix and export one tutorial, or one video per part (§ Parts)."""
    script = load_script(args.script)
    errors, warnings = validate_script(script)
    if errors:
        for e in errors:
            print("ERROR: " + e)
        return 1
    mode = args.voice or (script.get("voice") or {}).get("mode", "draft")
    return _run_each(_runs(script, args),
                     lambda run: _build_one(script, args, mode, warnings, *run))


def _build_one(script, args, mode, warnings, part, before, scenes, name):
    """Record, mix and export one video (§ Timing model 1-5)."""
    import audio
    import openscreen
    import srt
    import contact_sheet

    plain = name == script["code"]
    out = Path(args.out) if args.out else DEFAULT_OUT_ROOT / script["code"]
    out.mkdir(parents=True, exist_ok=True)
    # Parts share one folder: keep their logs, takes and contact sheets apart.
    log = Log(out / ("build.log" if not part else name + ".build.log"))
    take_name = "take" if not part else name + ".take"
    sheet_dir = out if not part else out / (name + "-sheets")
    steps_on = not args.no_steps
    log("build %s  (%s)  voice=%s quality=%s fps=%s zoom=%s steps=%s" % (
        name, time.strftime("%Y-%m-%d %H:%M"), mode, args.quality, args.fps,
        "off" if args.no_zoom else "on", "on" if steps_on else "off"))
    if part:
        log("part %s: %s" % (part, find_part(script, part).get("title", "")))
    for w in warnings:
        log("warning: " + w)

    # 1. Narration first, so every duration is known.
    clips = synthesize_all(scenes, mode, log, script)

    # 2. Stage the app and start recording.
    driver = _stage(script, log)
    timeline, rec, failed_checks = [], None, []
    try:
        _fast_forward(driver, before, log)
        title = driver.window_title()
        window_size = driver.window_size()
        matches = [w["name"] for w in openscreen.sources().get("windows", [])
                   if title.lower() in w["name"].lower()]
        if len(matches) > 1:
            log("  warning: %d windows contain %r: %s — the recorder takes the first"
                % (len(matches), title, matches))
        driver.bring_to_front()
        rec = openscreen.Recording(title, out / "take.openscreen", log=log).start()
        t0 = rec.wait_started()
        clock = lambda: time.time() - t0  # noqa: E731
        time.sleep(LEAD_IN)

        # 3. Scenes in real time.
        for scene, (clip, n) in zip(scenes, clips):
            entry = run_scene(driver, scene, n, clock, log, clip=clip, play=args.play,
                              measure_zoom=bool(scene.get("zoom")) and not args.no_zoom)
            entry["clip"] = str(clip) if clip else None
            timeline.append(entry)
            log("  %-18s %6.2f -> %6.2f  (voice %.1f s, actions done at +%.1f s)" % (
                scene["id"], entry["start"], entry["end"], n, entry["actions_end"] - entry["start"]))
            for a in entry["actions"]:
                log("      %-11s %-14s %6.2f -> %6.2f" % (a["do"], a["target"], a["start"], a["end"]))
            for res in entry["checks"]:
                log("      %s %s" % ("PASS" if res["pass"] else "FAIL", describe_check(res)))
            failed_checks += [r for r in entry["checks"] if not r["pass"]]
            if failed_checks and not args.no_check:
                raise SystemExit("check failed in scene %r; stopping the take "
                                 "(fix the script or pass --no-check)" % scene["id"])
        time.sleep(TAIL)
        done = rec.stop()
        rec = None
    finally:
        if rec is not None:
            rec.kill()
        driver.teardown(keep_open=args.keep_open)
        _write_checks(out / (name + ".checks.json"), script, timeline, mode)

    take_seconds = done.get("durationMs", 0) / 1000.0
    log("take: %.2f s recorded (recorder clock)" % take_seconds)

    # Step captions from the measured action times (§ Step captions).
    add_steps(timeline, scenes, initial_active(script, before))

    # 4-5. Project edits: 16:9 house style, hidden cursor, zooms + callouts + steps.
    project_path = Path(done.get("projectPath") or out / "take.openscreen")
    project = openscreen.load_project(project_path)
    video = openscreen.adopt_take(project, out, name=take_name)
    openscreen.apply_tutorial_style(project)
    zooms, notes = [], []
    if not args.no_zoom:
        zooms, notes = _regions(timeline, scenes, openscreen, log, window_size,
                                steps_on=steps_on)
    steps = step_regions(timeline, openscreen) if steps_on else []
    openscreen.set_regions(project, zooms, notes + steps)
    project_path = openscreen.save_project(project, out / (name + ".openscreen"))
    stale = out / "take.openscreen"
    if stale.exists() and stale != project_path:
        stale.unlink()
    log("project: %s (%d zoom, %d callout, %d step)" % (project_path.name, len(zooms),
                                                        len(notes), len(steps)))

    # The recorder's clock and the video file can disagree by a few frames.
    video_seconds = contact_sheet.video_duration(video) or take_seconds
    log("video: %.2f s (offset vs recorder clock %+.2f s)" % (video_seconds,
                                                               video_seconds - take_seconds))

    track = None
    if mode != "draft":
        track = audio.assemble([(e["start"], Path(e["clip"])) for e in timeline if e["clip"]],
                               out / (name + ".narration.wav"), total_seconds=video_seconds)
        log("narration track: %s" % track.name)
    mp4 = out / (name + ".mp4")
    result = openscreen.export(project_path, mp4, audio=track, quality=args.quality,
                               fps=args.fps, log=log)
    log("exported: %s (%sx%s)" % (mp4.name, result.get("width"), result.get("height")))

    srt.write_srt(narration_cues(timeline), out / (name + ".srt"))
    sheets = contact_sheet.make_sheets(mp4, sheet_dir, every=3.0)
    log("captions: %s; contact sheets: %d%s" % (name + ".srt", len(sheets),
                                                "" if plain or not part else " in " + sheet_dir.name))

    rows = []
    for e, scene in zip(timeline, scenes):
        rows.append({"id": e["id"], "start": e["start"], "end": e["end"], "narration": e["narration"],
                     "actions_s": e["actions_end"] - e["start"], "length": e["end"] - e["start"],
                     "checks_label": checks_label(e["checks"])})
    log("")
    log(scene_table(rows, "scene timing (seconds from t0 = first video frame)"))
    meta = {"code": name, "voice": mode, "lead_in": LEAD_IN, "breath": BREATH,
            "take_seconds": take_seconds, "video_seconds": video_seconds,
            "steps": steps_on, "scenes": timeline}
    if part:
        meta["part"] = part
    (out / (name + ".timeline.json")).write_text(json.dumps(meta, indent=2, default=str))
    log("done: %s" % mp4)
    all_checks = [r for e in timeline for r in e["checks"]]
    return {"rc": 1 if failed_checks and not args.no_check else 0, "name": name,
            "seconds": video_seconds, "checks": checks_label(all_checks), "file": str(mp4)}


def add_steps(timeline, scenes, active):
    """Write each scene's step captions ({start, end, text}) into its timeline
    entry; `active` is the sheet active when the first scene starts."""
    for entry, scene in zip(timeline, scenes):
        steps, active = scene_steps(scene, active)
        entry["steps"] = step_timings(entry, steps)
    return timeline


def _regions(timeline, scenes, openscreen, log, window_size=None, steps_on=False):
    """Camera zooms for scenes with `zoom`, text callouts for `callout`
    (§ Timing model 5). Focus math is approximate; see drivers/excel.py
    (range_rect) and openscreen.py (content_box, frame_focus, depth_for_scale).
    With step captions on, callouts sit above the step bar."""
    zooms, notes = [], []
    box = (1.0, 1.0)
    if window_size:
        box = openscreen.content_box(window_size[0], window_size[1],
                                     openscreen.TUTORIAL_EDITOR["padding"])
    for entry, scene in zip(timeline, scenes):
        rect = entry.get("zoom_rect")
        if scene.get("zoom"):
            if not rect:
                log("  warning: no on-screen position for zoom %s; skipped" % scene["zoom"])
            else:
                depth = openscreen.depth_for_scale(zoom_scale_for(rect))
                cx, cy = openscreen.frame_focus(rect[0] + rect[2] / 2, rect[1] + rect[3] / 2,
                                                openscreen.DEPTH_SCALE[depth], box)
                start = entry["start"] + 0.2
                end = max(start + 0.5, entry["end"] - 0.3)
                zooms.append(openscreen.zoom_region("zoom-" + scene["id"], start, end, cx, cy,
                                                    depth=depth))
        callout = scene.get("callout")
        if callout:
            span = entry["end"] - entry["start"]
            start = entry["start"] + float(callout.get("at", 0.3)) * span
            extra = {"y": CALLOUT_Y_WITH_STEPS} if steps_on else {}
            notes.append(openscreen.text_annotation("callout-" + scene["id"], start,
                                                    entry["end"], callout["text"], **extra))
    return zooms, notes


def _write_checks(path, script, timeline, mode):
    results = [r for e in timeline for r in e.get("checks", [])]
    path.write_text(json.dumps({
        "code": script["code"], "voice": mode, "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "passed": all(r["pass"] for r in results), "count": len(results), "results": results,
    }, indent=2, default=str))


# ===========================================================================
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="tutorial.py",
        description="Build a narrated, captioned screen tutorial from a *.tutorial.json script "
                    "(see references/script-format.md).")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="check the script; print estimated runtime per scene")
    p.add_argument("script")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("dryrun", help="drive the app and run every check, no recording")
    p.add_argument("script")
    p.add_argument("--voice", choices=VOICE_MODES, help="narration lengths from this voice (default draft)")
    p.add_argument("--chapter", help="only this chapter (earlier scenes are fast-forwarded)")
    p.add_argument("--part", help="only this part: its intro, chapters and outro")
    p.add_argument("--all-parts", action="store_true", help="every part in order, a fresh workbook each")
    p.add_argument("--live", action="store_true", help="real pacing (typing, at, waits) instead of fast")
    p.add_argument("--keep-open", action="store_true", help="leave the workbook open afterwards")
    p.set_defaults(func=cmd_dryrun)

    p = sub.add_parser("build", help="record, narrate and export the MP4 + SRT")
    p.add_argument("script")
    p.add_argument("--voice", choices=VOICE_MODES, help="narration mode (default: script voice.mode)")
    p.add_argument("--out", help="output folder (default videos/tutorials/out/<code>/)")
    p.add_argument("--chapter", help="record only this chapter")
    p.add_argument("--part", help="record only this part as <code>-<part> (earlier scenes fast-forwarded)")
    p.add_argument("--all-parts", action="store_true",
                   help="record every part as its own video; continues past a failed part")
    p.add_argument("--no-check", action="store_true", help="a failed check does not stop the build")
    p.add_argument("--no-zoom", action="store_true", help="no camera zooms or callouts")
    p.add_argument("--no-steps", action="store_true", help="no burned-in step captions")
    p.add_argument("--quality", choices=("medium", "good", "source"), default="good")
    p.add_argument("--fps", type=int, choices=(30, 60), default=30)
    p.add_argument("--play", action="store_true", help="play each clip aloud while recording")
    p.add_argument("--keep-open", action="store_true", help="leave the workbook open afterwards")
    p.set_defaults(func=cmd_build)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
