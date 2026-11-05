"""
cushman.py — shared house style + narration engine for Cushman Physics videos
=============================================================================

Every scene file in this folder imports from here:

    from cushman import *

What lives here (reuse it, don't re-derive it):
  - PALETTE / FONTS    the site's paper/ink/blue tokens (assets/css/site.css)
                       plus three series colors for multi-line graphs.
  - eq()               typeset an equation WITHOUT LaTeX: "v_f^2 = v_i^2 + 2aΔx"
                       becomes real sub/superscripts via Pango markup.
  - mono()/body()/display()   Text in the three site faces.
  - keep_in_frame()    nudge a computed label back inside the frame.
  - NarratedScene      Scene subclass whose animation is timed to a spoken
                       script. Declare SCRIPT (ordered dict of beat -> spoken
                       text) on the class, then wrap each stretch of animation
                       in `with self.narrate("beat") as b:`. The beat's audio
                       is attached at that moment and the block is padded so
                       the picture never runs ahead of (or behind) the voice.

Narration modes (env var NARRATION, set for you by render.sh):
  draft   (default) silent; beat lengths are ESTIMATED from word count. Free,
          instant — use this for every iteration on blocking and layout.
  eleven  ElevenLabs text-to-speech. Needs ELEVENLABS_API_KEY. Clips are cached
          by content hash in narration_cache/, so re-rendering an unchanged
          script costs nothing; editing one beat re-voices that beat and its
          two neighbors (their prosody context changed).
  say     macOS `say` — the no-network backup voice.

Writing SCRIPT text: it is fed to a speech engine verbatim, so write it the way
it is SPOKEN — "nine point eight meters per second squared", "v final", "one
half a t squared" — never "9.8 m/s²" or "v_f". Symbols belong on screen.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from manim import *

# ---------------------------------------------------------------------------
# Site palette (mirrors assets/css/site.css custom properties).
# ---------------------------------------------------------------------------
PAPER = "#F7F7F4"       # --paper       : scene background
PAPER_DEEP = "#EFEFEA"  # --paper-deep  : subtle panels
INK = "#141412"         # --ink         : primary text + strokes
INK_SOFT = "#6E6E68"    # --ink-soft    : secondary text, reference axes
LINE = "#E3E3DE"        # --line        : hairline rules, grid lines
BLUE = "#0E406A"        # --blue        : the hero element, title-card band
NAVY = "#005487"        # --navy
BRIGHT = "#0071CE"      # --bright      : a livelier blue for highlights
LIGHT_BLUE = "#7BADD3"  # --light-blue
PALE_BLUE = "#BDD4E7"   # --pale-blue   : soft fills (area under a curve)

# Series colors for scenes that track several quantities at once. One meaning
# per color across the whole unit, and always paired with a text label so
# nothing depends on color alone.
C_POS = BLUE            # position / displacement
C_VEL = "#0B7A66"       # velocity
C_ACC = "#C8501A"       # acceleration (and gravity)
C_HILITE = "#B8860B"    # a momentary "look here" (tangent line, callout)

FONT_DISPLAY = "Familjen Grotesk"            # headlines, title cards
FONT_BODY = "Atkinson Hyperlegible Next"     # sentences on screen
FONT_MONO = "Fragment Mono"                  # labels, numbers, equations

config.background_color = PAPER


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def mono(text, size=26, color=INK, **kw):
    """Label / number / unit in Fragment Mono."""
    return Text(text, font=FONT_MONO, font_size=size, color=color, **kw)


def body(text, size=28, color=INK, **kw):
    """A sentence on screen, in the site's body face."""
    kw.setdefault("line_spacing", 1.15)
    return Text(text, font=FONT_BODY, font_size=size, color=color, **kw)


def display(text, size=52, color=INK, **kw):
    """Headline in Familjen Grotesk."""
    kw.setdefault("weight", BOLD)
    return Text(text, font=FONT_DISPLAY, font_size=size, color=color, **kw)


_SCRIPT_RE = re.compile(r"([_^])(\{[^}]*\}|[^\s{}])")


def eq(expr, size=34, color=INK, font=FONT_MONO, **kw):
    """Typeset an equation with real sub/superscripts and no LaTeX.

        eq("v_f = v_i + at")
        eq("Δx = v_i t + ½at^2")
        eq("v_f^2 = v_i^2 + 2aΔx", color=BLUE)
        eq("x ∝ t^2"), eq("a_{avg}")

    `_x` / `^x` script one character; `_{...}` / `^{...}` script a group.
    Unicode does the rest (Δ θ ½ × ≈ ∝ → ·). To color one piece, pass Pango
    markup straight through: eq('<span foreground="%s">v_x</span> = v cos θ' % C_VEL).
    """
    def repl(m):
        tag = "sub" if m.group(1) == "_" else "sup"
        return f"<{tag}>{m.group(2).strip('{}')}</{tag}>"

    # Script markers are only converted outside existing <...> tags.
    parts = re.split(r"(<[^>]+>)", expr.replace("&", "&amp;"))
    markup = "".join(p if p.startswith("<") else _SCRIPT_RE.sub(repl, p) for p in parts)
    return MarkupText(markup, font=font, font_size=size, color=color, **kw)


def keep_in_frame(mobject, margin=0.4):
    """Shift a mobject so it sits fully inside the visible frame (both axes).
    Use on any label whose size depends on computed text."""
    x_lim = config.frame_x_radius - margin
    y_lim = config.frame_y_radius - margin
    if mobject.get_right()[0] > x_lim:
        mobject.shift(LEFT * (mobject.get_right()[0] - x_lim))
    if mobject.get_left()[0] < -x_lim:
        mobject.shift(RIGHT * (-x_lim - mobject.get_left()[0]))
    if mobject.get_top()[1] > y_lim:
        mobject.shift(DOWN * (mobject.get_top()[1] - y_lim))
    if mobject.get_bottom()[1] < -y_lim:
        mobject.shift(UP * (-y_lim - mobject.get_bottom()[1]))
    return mobject


# ---------------------------------------------------------------------------
# Narration engine
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "narration_cache"
CAPTION_DIR = HERE / "captions"

NARRATION_MODE = os.environ.get("NARRATION", "draft").lower()

# Backup narrator until Willie's own cloned voice exists in the ElevenLabs
# account: "Brian — Deep, Resonant and Comforting". To switch every video to
# the clone, set ELEVEN_VOICE_ID (render.sh reads it from voice.env).
ELEVEN_VOICE_ID = os.environ.get("ELEVEN_VOICE_ID", "nPczCjzI2devNBz1zQrb")
ELEVEN_MODEL = os.environ.get("ELEVEN_MODEL", "eleven_multilingual_v2")
ELEVEN_SETTINGS = {
    "stability": float(os.environ.get("ELEVEN_STABILITY", 0.42)),   # lower = more expressive, less monotone
    "similarity_boost": float(os.environ.get("ELEVEN_SIMILARITY", 0.8)),
    "style": 0.35,              # ignored by the v4 models (only stability/similarity count)
    "speed": 0.94,              # the stock narrator runs a touch fast for new material
    "use_speaker_boost": True,
}
SAY_VOICE = os.environ.get("SAY_VOICE", "Daniel")

WORDS_PER_SECOND = 2.9  # draft-mode pacing estimate, measured against the narrator


def _estimate_duration(text):
    return max(1.5, len(text.split()) / WORDS_PER_SECOND)


def _probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


# Delivery direction for the v3/v4 models: a bracketed audio tag such as
# "[dry, wry, understated]" prepended to every beat. Not spoken, not captioned.
ELEVEN_DIRECTION = os.environ.get("ELEVEN_DIRECTION", "").strip()


def _directed(text):
    return f"{ELEVEN_DIRECTION} {text}" if ELEVEN_DIRECTION else text


def _eleven_synthesize(text, prev_text, next_text, dest):
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("NARRATION=eleven needs ELEVENLABS_API_KEY in the environment")
    payload = {"text": _directed(text), "model_id": ELEVEN_MODEL, "voice_settings": ELEVEN_SETTINGS}
    # Neighboring beats as context so each clip's intonation flows into the next.
    if prev_text:
        payload["previous_text"] = prev_text
    if next_text:
        payload["next_text"] = next_text
    request = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"
        "?output_format=mp3_44100_128",
        data=json.dumps(payload).encode(),
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            dest.write_bytes(response.read())
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"ElevenLabs {err.code}: {err.read().decode(errors='replace')[:300]}")


def _say_synthesize(text, dest):
    aiff = dest.with_suffix(".aiff")
    subprocess.run(["say", "-v", SAY_VOICE, "-o", str(aiff), text], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), str(dest)], check=True)
    aiff.unlink()


def narration_clip(text, prev_text=None, next_text=None):
    """Return (audio_path_or_None, duration_seconds) for one beat of narration."""
    if NARRATION_MODE == "draft":
        return None, _estimate_duration(text)

    if NARRATION_MODE == "eleven":
        identity = [ELEVEN_VOICE_ID, ELEVEN_MODEL, ELEVEN_SETTINGS, ELEVEN_DIRECTION, text, prev_text, next_text]
        folder = CACHE_DIR / ELEVEN_VOICE_ID
    elif NARRATION_MODE == "say":
        identity = [SAY_VOICE, text]
        folder = CACHE_DIR / f"say-{SAY_VOICE}"
    else:
        raise ValueError(f"NARRATION must be draft, eleven or say (got {NARRATION_MODE!r})")

    digest = hashlib.sha1(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    folder.mkdir(parents=True, exist_ok=True)
    clip = folder / f"{digest}.mp3"
    if not clip.exists():
        partial = clip.with_suffix(".part.mp3")
        if NARRATION_MODE == "eleven":
            _eleven_synthesize(text, prev_text, next_text, partial)
        else:
            _say_synthesize(text, partial)
        partial.rename(clip)
    return clip, _probe_duration(clip)


class Beat:
    """Handle yielded by NarratedScene.narrate(). Use it to pace the animation
    inside the block against the length of the spoken line."""

    def __init__(self, scene, duration):
        self.scene = scene
        self.duration = duration
        self.start = scene.time

    @property
    def elapsed(self):
        return self.scene.time - self.start

    @property
    def remaining(self):
        return max(0.0, self.duration - self.elapsed)

    def span(self, fraction, floor=0.4):
        """A run_time that makes the next play() END at `fraction` of the line:
        self.play(Create(curve), run_time=b.span(0.6))"""
        return max(floor, fraction * self.duration - self.elapsed)

    def until(self, fraction):
        """Hold still until `fraction` of the line has been spoken."""
        self._wait(fraction * self.duration - self.elapsed)

    def finish(self):
        self._wait(self.remaining)

    def _wait(self, seconds):
        if seconds > 1.5 / config.frame_rate:
            self.scene.wait(seconds)


class NarratedScene(Scene):
    """Scene timed to a spoken script.

        class FreeFall(NarratedScene):
            VIDEO_CODE = "PHY-U1-free-fall"
            TITLE = "Free Fall"
            SUBTITLE = "Physics · Unit 1 · Kinematics"
            SCRIPT = {
                "hook": "Drop a hammer and a feather on the Moon...",
                "g":    "Near Earth's surface, that number is nine point eight...",
            }

            def construct(self):
                with self.narrate("hook") as b:
                    self.play(FadeIn(moon), run_time=b.span(0.3))
                    b.until(0.7)                 # hold until the punchline
                    self.play(Indicate(hammer))
                # leaving the block waits out whatever is left of the line
                with self.narrate("g") as b:
                    ...
                self.end_card()

    Rules of the road:
      - Every beat in SCRIPT must be narrated exactly once, in order.
      - Animation inside a block may run LONGER than the line (the next line
        simply starts later) but should not: aim to land on b.duration.
      - Never hardcode a beat's length; real audio differs from the draft
        estimate. Pace with b.span() / b.until() / b.remaining.
    """

    VIDEO_CODE = ""
    TITLE = ""
    SUBTITLE = ""
    SCRIPT: dict[str, str] = {}
    BEAT_GAP = 0.4  # breath between lines, seconds

    def setup(self):
        super().setup()
        self._beat_log = []
        self._beat_keys = list(self.SCRIPT)

    @contextmanager
    def narrate(self, key, gap=None):
        index = self._beat_keys.index(key)
        expected = len(self._beat_log)
        if index != expected:
            raise RuntimeError(
                f"Beat {key!r} narrated out of order (expected {self._beat_keys[expected]!r})"
            )
        text = self.SCRIPT[key]
        prev_text = self.SCRIPT[self._beat_keys[index - 1]] if index > 0 else None
        next_text = (
            self.SCRIPT[self._beat_keys[index + 1]] if index + 1 < len(self._beat_keys) else None
        )
        clip, duration = narration_clip(text, prev_text, next_text)
        if clip is not None:
            self.add_sound(str(clip))
        beat = Beat(self, duration)
        yield beat
        beat.finish()
        self._beat_log.append((key, text, beat.start, beat.start + duration))
        pause = self.BEAT_GAP if gap is None else gap
        if pause > 0:
            self.wait(pause)

    # -- shared cards ---------------------------------------------------------
    def clear(self, run_time=0.8):
        """Fade everything off before a new section or the end card."""
        if self.mobjects:
            self.play(FadeOut(Group(*self.mobjects)), run_time=run_time)

    def end_card(self, hold=3.0):
        """The closer every video shares: headline, course line, blue band,
        video code. Reads TITLE / SUBTITLE / VIDEO_CODE off the class."""
        self.clear()
        headline = display(self.TITLE)
        subtitle = mono(self.SUBTITLE, size=26, color=INK_SOFT)
        subtitle.next_to(headline, DOWN, buff=0.35)
        band = Rectangle(
            width=max(headline.width, subtitle.width) + 0.6, height=0.12,
            fill_color=BLUE, fill_opacity=1, stroke_width=0,
        ).next_to(subtitle, DOWN, buff=0.45)
        code = mono(self.VIDEO_CODE, size=20, color=INK_SOFT).next_to(band, DOWN, buff=0.6)
        card = VGroup(headline, subtitle, band, code).move_to(ORIGIN)
        self.play(FadeIn(card, shift=UP * 0.2), run_time=1.2)
        self.wait(hold)

    # -- captions -------------------------------------------------------------
    def tear_down(self):
        super().tear_down()
        missing = [k for k in self._beat_keys if k not in {b[0] for b in self._beat_log}]
        if missing:
            logger.warning(f"SCRIPT beats never narrated: {missing}")
        if self.VIDEO_CODE and self._beat_log:
            self._write_captions()

    def _write_captions(self):
        """Write captions/<VIDEO_CODE>.srt from the beat timings — upload it
        alongside the video so the narration is readable as well as audible."""
        cues = []
        for _, text, start, end in self._beat_log:
            sentences = [s for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s]
            total = sum(len(s) for s in sentences)
            cursor = start
            for sentence in sentences:
                length = (end - start) * len(sentence) / total
                cues.append((cursor, cursor + length, sentence))
                cursor += length

        def stamp(seconds):
            millis = round(seconds * 1000)
            return "%02d:%02d:%02d,%03d" % (
                millis // 3600000, millis // 60000 % 60, millis // 1000 % 60, millis % 1000,
            )

        CAPTION_DIR.mkdir(exist_ok=True)
        suffix = "" if NARRATION_MODE != "draft" else ".draft"
        lines = [
            f"{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n"
            for i, (a, b, text) in enumerate(cues, 1)
        ]
        (CAPTION_DIR / f"{self.VIDEO_CODE}{suffix}.srt").write_text("\n".join(lines))
