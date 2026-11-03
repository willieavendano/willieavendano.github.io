"""OpenScreen CLI wrapper + project-file editing for the tutorial pipeline.

Implements the recorder half of `references/script-format.md § Timing model`:
start a window recording, report `t0` (the wall-clock moment the recorder
logs "Recording started"), stop it, then edit the `.openscreen` project
(16:9 frame, padding, camera zooms, text callouts) and export the MP4 with
the narration track swapped in (`--audio track.wav --audio-mode replace`).

The CLI is the app binary itself. Inside Claude Code / T3 Code sessions
`ELECTRON_RUN_AS_NODE=1` is set, which turns the binary into plain Node, so
every call runs with that variable removed.

Project file facts (OpenScreen 2.2.1, read from the app's own normalizer in
app.asar `projectPersistence-*.js` and verified by exporting):

    zoomRegions[]:       {id, startMs, endMs, depth 1-6, focus {cx, cy} (0-1 of the
                          OUTPUT FRAME, moved to the frame centre at full zoom;
                          no clamping by the app), focusMode "manual"|"auto",
                          source "manual"|"auto", rotationPreset?}
                          depth -> scale: 1:1.25 2:1.5 3:1.8 4:2.2 5:3.5 6:5
                          (the editor also knows `customScale`, but the project
                          loader drops it, so only depth reaches the export)
    annotationRegions[]: {id, startMs, endMs, type "text"|"image"|"figure"|"blur",
                          content, textContent?, position {x, y} (0-100 % of the frame),
                          size {width, height} (1-200 %), zIndex,
                          style {color, backgroundColor, fontSize, fontFamily
                          (Inter|Lora|Oswald|Caveat|IBM Plex Mono), fontWeight
                          normal|bold, fontStyle, textDecoration, textAlign,
                          textAnimation none|fade|rise|pop|slide-left|typewriter|pulse}}
    Unknown keys are dropped when the app loads a project.
"""

import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path

BINARY = "/Applications/Openscreen.app/Contents/MacOS/Openscreen"

# Zoom depth -> magnification, from the app (const Vp in index-*.js).
DEPTH_SCALE = {1: 1.25, 2: 1.5, 3: 1.8, 4: 2.2, 5: 3.5, 6: 5.0}

# House style for tutorials: a 16:9 frame (YouTube/Canvas players), a thin
# wallpaper margin and small corner radius so the cells stay as big as possible.
TUTORIAL_EDITOR = {
    "aspectRatio": "16:9",
    "padding": 24,
    "borderRadius": 12,
    "shadowIntensity": 0.35,
    "motionBlurAmount": 0.0,     # motion blur smears text during camera moves
    "depthOfField": False,
    "autoZoomEnabled": False,    # our zooms come from the script, not the cursor
    "autoFocusAll": False,
}

CALLOUT_STYLE = {
    "color": "#ffffff",
    "backgroundColor": "#1f2937",
    "fontSize": 44,
    "fontFamily": "Inter",
    "fontWeight": "bold",
    "fontStyle": "normal",
    "textDecoration": "none",
    "textAlign": "center",
    "textAnimation": "pop",
}


class OpenScreenError(RuntimeError):
    pass


def binary():
    path = os.environ.get("OPENSCREEN_BIN", BINARY)
    if not Path(path).exists():
        raise OpenScreenError("OpenScreen not found at %s (run scripts/setup.sh)" % path)
    return path


def cli_env():
    """The session environment minus ELECTRON_RUN_AS_NODE (see module doc)."""
    env = dict(os.environ)
    env.pop("ELECTRON_RUN_AS_NODE", None)
    return env


def _events(lines):
    for line in lines:
        line = line.strip()
        if line.startswith("{"):
            try:
                yield json.loads(line)
            except ValueError:
                continue


def run_json(args, timeout=900, on_event=None):
    """Run one CLI command with --json; return its `done` event."""
    proc = subprocess.Popen([binary()] + list(args) + ["--json"], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, env=cli_env())
    done = None
    deadline = time.time() + timeout
    for event in _events(iter(proc.stdout.readline, "")):
        if on_event:
            on_event(event)
        if event.get("event") == "done":
            done = event
        if time.time() > deadline:
            proc.kill()
            raise OpenScreenError("openscreen %s timed out" % args[0])
    proc.wait()
    err = proc.stderr.read()
    if not done or not done.get("success", False):
        reason = (done or {}).get("error") or err.strip()[-800:]
        raise OpenScreenError("openscreen %s failed: %s" % (args[0], reason))
    return done


def sources():
    """Windows and displays OpenScreen can record: the `done` event's dict."""
    return run_json(["sources"], timeout=60).get("sources", {})


def info(project):
    """`openscreen info --json`: one plain JSON object (no NDJSON events)."""
    proc = subprocess.run([binary(), "info", str(project), "--json"], capture_output=True,
                          text=True, env=cli_env(), timeout=60)
    for line in proc.stdout.splitlines():
        if line.strip().startswith("{"):
            return json.loads(line)
    raise OpenScreenError("openscreen info failed: %s" % (proc.stderr.strip()[-600:]))


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------
class Recording:
    """An untimed window recording, stopped by writing "stop" to stdin.

        rec = Recording(window_title, project_path).start()
        t0 = rec.wait_started()        # wall clock (time.time()) of frame zero
        ...drive the app...
        done = rec.stop()              # {screenVideoPath, durationMs, projectPath...}
    """

    def __init__(self, window, project, cursor="editable-overlay", log=print):
        self.window = window
        self.project = Path(project)
        self.cursor = cursor
        self.log = log
        self.proc = None
        self.t0 = None
        self.done = None
        self._events = queue.Queue()
        self._stderr = []

    def start(self):
        self.project.parent.mkdir(parents=True, exist_ok=True)
        args = [binary(), "record", "--window", self.window, "--cursor", self.cursor,
                "--project", str(self.project), "--json"]
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, env=cli_env(), bufsize=1)
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        return self

    def _read_stdout(self):
        for line in iter(self.proc.stdout.readline, ""):
            stamp = time.time()
            for event in _events([line]):
                self._events.put((stamp, event))

    def _read_stderr(self):
        for line in iter(self.proc.stderr.readline, ""):
            self._stderr.append(line)

    def _next(self, timeout):
        try:
            return self._events.get(timeout=timeout)
        except queue.Empty:
            return None, None

    def wait_started(self, timeout=45):
        """Block until the recorder logs "Recording started"; return that time."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            stamp, event = self._next(0.5)
            if event is None:
                if self.proc.poll() is not None:
                    break
                continue
            if event.get("event") == "log":
                self.log("  recorder: %s" % event.get("message"))
                if event.get("message") == "Recording started":
                    self.t0 = stamp
                    return stamp
            if event.get("event") == "done":
                self.done = event
                raise OpenScreenError("recorder stopped before starting: %s"
                                      % (event.get("error") or "".join(self._stderr)[-600:]))
        self.kill()
        raise OpenScreenError("recorder did not start within %ss: %s"
                              % (timeout, "".join(self._stderr)[-600:]))

    def stop(self, timeout=120):
        """Ask the recorder to stop; return its `done` event."""
        if self.done:
            return self.done
        try:
            self.proc.stdin.write("stop\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            self.proc.send_signal(2)
        deadline = time.time() + timeout
        while time.time() < deadline:
            _, event = self._next(0.5)
            if event and event.get("event") == "done":
                self.done = event
                break
            if event is None and self.proc.poll() is not None:
                break
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.kill()
        if not self.done or not self.done.get("success"):
            raise OpenScreenError("recording failed: %s" % (
                (self.done or {}).get("error") or "".join(self._stderr)[-800:]))
        return self.done

    def kill(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export(project, out, audio=None, quality="good", fps=30, log=print):
    """Render the project to MP4, replacing its audio with `audio` if given."""
    args = ["export", str(project), "-o", str(out), "--quality", quality, "--fps", str(fps)]
    if audio:
        args += ["--audio", str(audio), "--audio-mode", "replace"]
    last = [0.0]

    def progress(event):
        pct = event.get("percent") or event.get("progress")
        if isinstance(pct, (int, float)):
            pct = pct * 100 if pct <= 1 else pct
            if pct - last[0] >= 20:
                last[0] = pct
                log("  export %3.0f%%" % pct)

    return run_json(args, timeout=1800, on_event=progress)


# ---------------------------------------------------------------------------
# Project-file editing (pure functions; unit-tested)
# ---------------------------------------------------------------------------
def load_project(path):
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or "editor" not in data or "media" not in data:
        raise OpenScreenError("%s is not an OpenScreen project" % path)
    return data


def save_project(project, path):
    Path(path).write_text(json.dumps(project, indent=2))
    return Path(path)


def apply_tutorial_style(project, overrides=None):
    """16:9 frame, thin padding, small radius, no automatic zooms."""
    editor = project.setdefault("editor", {})
    editor.update(TUTORIAL_EDITOR)
    if overrides:
        editor.update(overrides)
    return project


def adopt_take(project, dest_dir, name="take", hide_cursor=True):
    """Move the raw recording (and its cursor track) out of OpenScreen's
    recordings folder into the build folder, so each build is self-contained,
    and point the project at it.

    With `hide_cursor` every cursor sample is marked invisible. The tutorial
    is driven by AppleScript, so the real pointer never moves; without this
    the exporter draws an arrow parked over the sheet for the whole video.
    (Setting media.cursorCaptureMode alone does not stop the overlay.)
    """
    import shutil
    media = project["media"]
    src = Path(media["screenVideoPath"])
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    video = dest_dir / (name + src.suffix)
    if src.resolve() != video.resolve():
        shutil.move(str(src), str(video))
        cursor_src = Path(str(src) + ".cursor.json")
        if cursor_src.exists():
            shutil.move(str(cursor_src), str(video) + ".cursor.json")
    media["screenVideoPath"] = str(video)
    cursor = Path(str(video) + ".cursor.json")
    if hide_cursor and cursor.exists():
        track = json.loads(cursor.read_text())
        for sample in track.get("samples", []):
            sample["visible"] = False
        cursor.write_text(json.dumps(track))
    return video


def zoom_region(region_id, start_s, end_s, cx, cy, depth=2):
    """A manual camera zoom over [start_s, end_s], focus (cx, cy) in output-
    frame fractions (see frame_focus). Magnification comes from `depth` only:
    the app's project loader drops `customScale`, so it never reaches export."""
    start_ms = int(round(start_s * 1000))
    end_ms = max(start_ms + 1, int(round(end_s * 1000)))
    return {
        "id": region_id,
        "startMs": start_ms,
        "endMs": end_ms,
        "depth": int(depth) if int(depth) in DEPTH_SCALE else 2,
        "focus": {"cx": _clamp(cx, 0.0, 1.0), "cy": _clamp(cy, 0.0, 1.0)},
        "focusMode": "manual",
        "source": "manual",
    }


def depth_for_scale(scale):
    """Deepest zoom depth whose magnification does not exceed `scale`
    (never less than depth 1 = 1.25x)."""
    fitting = [d for d, s in DEPTH_SCALE.items() if s <= scale + 1e-9]
    return max(fitting) if fitting else 1


def content_box(window_w, window_h, padding=24, frame_aspect=16 / 9):
    """(width, height) of the recorded window as fractions of the output frame.

    Empirical: padding p leaves (1 - p/240) of the frame's limiting
    dimension for the window (measured at padding 24 on a 1600x923 window
    in a 16:9 frame: 0.88 x 0.90). The other dimension follows the window's
    aspect ratio.
    """
    inner = 1 - float(padding) / 240
    aspect = float(window_w) / float(window_h)
    if aspect < frame_aspect:
        return inner * aspect / frame_aspect, inner
    return inner, inner * frame_aspect / aspect


# Measured on 1.5x and 1.8x exports: the rendered view sits ~2% of the frame
# right/down of where the centring model puts it. Letting the clamp reach this
# far past the window's edge keeps Excel's row and column headers in view
# (they tell the student which cell is which) at the cost of, at most, a
# hairline of wallpaper.
EDGE_SLACK = 0.03


def frame_focus(cx, cy, scale, box=(1.0, 1.0), slack=EDGE_SLACK):
    """Window-relative point -> zoom focus in output-frame fractions, clamped
    so the zoomed view stays on the recorded window.

    OpenScreen's zoom (AiEditionShell `focusX * stageWidth`) treats focus as
    a fraction of the output frame and, at full zoom, moves that point to the
    frame centre; the view is then 1/scale of the frame around it, with no
    clamping of its own. The window sits centred in the frame filling `box`
    (see content_box), so we map the point into frame coordinates and keep
    the view's edges inside the window's edges (give or take `slack`).
    Approximate: good to a few percent of the frame.
    """
    bw, bh = box
    mx, my = (1 - bw) / 2, (1 - bh) / 2
    fx, fy = mx + cx * bw, my + cy * bh
    half = 0.5 / max(scale, 1.0)
    if half * 2 >= bw:
        fx = 0.5
    else:
        fx = _clamp(fx, mx + half - slack, mx + bw - half + slack)
    if half * 2 >= bh:
        fy = 0.5
    else:
        fy = _clamp(fy, my + half - slack, my + bh - half + slack)
    return fx, fy


def text_annotation(region_id, start_s, end_s, text, x=50, y=86, width=44, height=9,
                    style=None, z_index=10):
    """A text callout. position/size are % of the output frame; (x, y) is the
    box's top-left corner (the app's default box is at 50,50 with 30x20)."""
    start_ms = int(round(start_s * 1000))
    st = dict(CALLOUT_STYLE)
    if style:
        st.update(style)
    return {
        "id": region_id,
        "startMs": start_ms,
        "endMs": max(start_ms + 1, int(round(end_s * 1000))),
        "type": "text",
        "content": text,
        "textContent": text,
        "position": {"x": _clamp(x, 0, 100), "y": _clamp(y, 0, 100)},
        "size": {"width": _clamp(width, 1, 200), "height": _clamp(height, 1, 200)},
        "style": st,
        "zIndex": z_index,
    }


def set_regions(project, zooms=None, annotations=None):
    """Replace the project's zoomRegions / annotationRegions (None = keep)."""
    editor = project.setdefault("editor", {})
    if zooms is not None:
        editor["zoomRegions"] = list(zooms)
    if annotations is not None:
        editor["annotationRegions"] = list(annotations)
    return project


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))
