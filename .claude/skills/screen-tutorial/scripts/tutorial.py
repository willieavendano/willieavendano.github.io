#!/usr/bin/env python3
"""Screen-tutorial builder: a JSON script in, a narrated, captioned MP4 out.

    tutorial.py validate <script.tutorial.json>
    tutorial.py dryrun   <script> [--voice draft|say|eleven] [--live] [--chapter ID] [--keep-open]
    tutorial.py build    <script> [--voice draft|say|eleven] [--out DIR] [--chapter ID]
                                  [--no-check] [--no-zoom] [--quality medium|good|source]
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

    scenes = script.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes: must be a non-empty list")
        return errors, warnings

    ids = []
    known_sheets = set(sheets)
    for i, scene in enumerate(scenes, start=1):
        where = "scene %d" % i
        if not isinstance(scene, dict):
            errors.append("%s: must be an object" % where)
            continue
        sid = scene.get("id")
        if not isinstance(sid, str) or not ID_RE.match(sid):
            errors.append("%s: `id` must be kebab-case" % where)
        else:
            where = "scene %r" % sid
            if sid in ids:
                errors.append("%s: duplicate id" % where)
            ids.append(sid)
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
    return errors, warnings


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
def synthesize_all(scenes, mode, log):
    """[(clip_path_or_None, seconds)] for each scene; neighbours as context."""
    import narration
    out = []
    for i, scene in enumerate(scenes):
        prev_text = scenes[i - 1]["say"] if i > 0 else None
        next_text = scenes[i + 1]["say"] if i + 1 < len(scenes) else None
        clip, seconds = narration.synthesize(scene["say"], mode, CACHE_DIR,
                                             prev_text=prev_text, next_text=next_text)
        out.append((clip, seconds))
    log("narration: %d clips (%s), %.1f s of speech" % (len(out), mode, sum(s for _, s in out)))
    return out


# ===========================================================================
# Commands
# ===========================================================================
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
    rows = []
    for scene in script["scenes"]:
        n = estimate_narration(scene["say"])
        plan = plan_scene(n, scene.get("actions", []))
        rows.append({"id": scene["id"], "narration": n, "actions_s": plan["actions"],
                     "length": plan["duration"],
                     "checks_label": "%d" % len(scene.get("checks", []) or [])})
    print(scene_table(rows, "%s — %s (draft estimates; checks not run)" % (script["code"],
                                                                         script["title"])))
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


def cmd_dryrun(args):
    """Drive the app and run every check without recording (fast by default)."""
    script = load_script(args.script)
    errors, warnings = validate_script(script)
    if errors:
        for e in errors:
            print("ERROR: " + e)
        return 1
    mode = args.voice or "draft"
    log = Log()
    before, scenes, _ = chapter_scenes(script, args.chapter)
    clips = synthesize_all(scenes, mode, log) if mode != "draft" else \
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
        script["code"], mode, ", live pacing" if args.live else "; lengths are estimates")))
    log("checks: %s" % ("all %d passed" % len(all_checks) if not failed else "FAILED"))
    return 1 if failed else 0


def cmd_build(args):
    """Record, mix and export one tutorial (§ Timing model 1-5)."""
    import audio
    import openscreen
    import srt
    import contact_sheet

    script = load_script(args.script)
    errors, warnings = validate_script(script)
    if errors:
        for e in errors:
            print("ERROR: " + e)
        return 1
    mode = args.voice or (script.get("voice") or {}).get("mode", "draft")
    before, scenes, _ = chapter_scenes(script, args.chapter)
    name = script["code"] + ("-" + args.chapter if args.chapter else "")
    out = Path(args.out) if args.out else DEFAULT_OUT_ROOT / script["code"]
    out.mkdir(parents=True, exist_ok=True)
    log = Log(out / "build.log")
    log("build %s  (%s)  voice=%s quality=%s fps=%s zoom=%s" % (
        name, time.strftime("%Y-%m-%d %H:%M"), mode, args.quality, args.fps,
        "off" if args.no_zoom else "on"))
    for w in warnings:
        log("warning: " + w)

    # 1. Narration first, so every duration is known.
    clips = synthesize_all(scenes, mode, log)

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

    # 4-5. Project edits: 16:9 house style, hidden cursor, zooms + callouts.
    project_path = Path(done.get("projectPath") or out / "take.openscreen")
    project = openscreen.load_project(project_path)
    video = openscreen.adopt_take(project, out, name="take")
    openscreen.apply_tutorial_style(project)
    zooms, notes = [], []
    if not args.no_zoom:
        zooms, notes = _regions(timeline, scenes, openscreen, log, window_size)
    openscreen.set_regions(project, zooms, notes)
    project_path = openscreen.save_project(project, out / (name + ".openscreen"))
    stale = out / "take.openscreen"
    if stale.exists() and stale != project_path:
        stale.unlink()
    log("project: %s (%d zoom, %d callout)" % (project_path.name, len(zooms), len(notes)))

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
    sheets = contact_sheet.make_sheets(mp4, out, every=3.0)
    log("captions: %s; contact sheets: %d" % (name + ".srt", len(sheets)))

    rows = []
    for e, scene in zip(timeline, scenes):
        rows.append({"id": e["id"], "start": e["start"], "end": e["end"], "narration": e["narration"],
                     "actions_s": e["actions_end"] - e["start"], "length": e["end"] - e["start"],
                     "checks_label": checks_label(e["checks"])})
    log("")
    log(scene_table(rows, "scene timing (seconds from t0 = first video frame)"))
    (out / (name + ".timeline.json")).write_text(json.dumps(
        {"code": name, "voice": mode, "lead_in": LEAD_IN, "breath": BREATH,
         "take_seconds": take_seconds, "video_seconds": video_seconds, "scenes": timeline},
        indent=2, default=str))
    log("done: %s" % mp4)
    return 1 if failed_checks and not args.no_check else 0


def _regions(timeline, scenes, openscreen, log, window_size=None):
    """Camera zooms for scenes with `zoom`, text callouts for `callout`
    (§ Timing model 5). Focus math is approximate; see drivers/excel.py
    (range_rect) and openscreen.py (content_box, frame_focus, depth_for_scale)."""
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
            notes.append(openscreen.text_annotation("callout-" + scene["id"], start,
                                                    entry["end"], callout["text"]))
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
    p.add_argument("--live", action="store_true", help="real pacing (typing, at, waits) instead of fast")
    p.add_argument("--keep-open", action="store_true", help="leave the workbook open afterwards")
    p.set_defaults(func=cmd_dryrun)

    p = sub.add_parser("build", help="record, narrate and export the MP4 + SRT")
    p.add_argument("script")
    p.add_argument("--voice", choices=VOICE_MODES, help="narration mode (default: script voice.mode)")
    p.add_argument("--out", help="output folder (default videos/tutorials/out/<code>/)")
    p.add_argument("--chapter", help="record only this chapter")
    p.add_argument("--no-check", action="store_true", help="a failed check does not stop the build")
    p.add_argument("--no-zoom", action="store_true", help="no camera zooms or callouts")
    p.add_argument("--quality", choices=("medium", "good", "source"), default="good")
    p.add_argument("--fps", type=int, choices=(30, 60), default=30)
    p.add_argument("--play", action="store_true", help="play each clip aloud while recording")
    p.add_argument("--keep-open", action="store_true", help="leave the workbook open afterwards")
    p.set_defaults(func=cmd_build)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
