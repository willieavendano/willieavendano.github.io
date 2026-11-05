"""
narration.py — one spoken beat in, one WAV out
==============================================

The screen-tutorial pipeline synthesizes every scene's narration *before*
recording, so each duration is known up front (script-format.md, "Timing
model"). This module is the only place that talks to a voice engine.

Modes (the `voice.mode` field in a tutorial JSON, or `--voice`):

  draft   No audio: (None, estimated_seconds). Free and instant — use it for
          every iteration on blocking.
  say     macOS `say`, converted to WAV with afconvert. The no-network backup.
  eleven  ElevenLabs text-to-speech (needs ELEVENLABS_API_KEY), converted to
          the same WAV spec with afconvert.

This is a port of the narration engine in videos/manim/cushman.py: same
request body, same voice settings, same cache-by-content-hash idea, same
neighbouring-beats-as-context trick. Differences are forced by the machine:
there is no ffmpeg, so afconvert does the format work and the `wave` module
reads durations straight from the WAV header.

Both real modes cache in `<cache_dir>/<voice-id-or-mode>/<sha1>.wav`, keyed on
everything that can change the audio (voice, model, settings, text, and the
neighbouring lines used for prosody). Re-rendering an unchanged script costs
nothing; editing one beat re-voices that beat and its two neighbours.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Optional, Tuple

WORDS_PER_SECOND = 2.9  # draft-mode pacing estimate, measured against the narrator

# Backup narrator until Willie's own cloned voice exists in the ElevenLabs
# account: "Brian — Deep, Resonant and Comforting". Set ELEVEN_VOICE_ID to
# switch every video to the clone.
def _load_voice_env():
    """Fallback narrator settings from videos/manim/voice.env (shared with the
    Manim pipeline): KEY=VALUE lines, environment wins."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        f = parent / "videos" / "manim" / "voice.env"
        if f.is_file():
            for line in f.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
            return


_load_voice_env()
ELEVEN_VOICE_ID = os.environ.get("ELEVEN_VOICE_ID", "nPczCjzI2devNBz1zQrb")
ELEVEN_MODEL = os.environ.get("ELEVEN_MODEL", "eleven_multilingual_v2")
ELEVEN_SETTINGS = {
    "stability": 0.42,          # lower = more expressive, less monotone
    "similarity_boost": 0.8,
    "style": 0.35,
    "speed": 0.94,              # the stock narrator runs a touch fast for new material
    "use_speaker_boost": True,
}
SAY_VOICE = os.environ.get("SAY_VOICE", "Daniel")

ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
ENV_FILE = Path.home() / ".hermes" / ".env"

WAV_FORMAT = ["-f", "WAVE", "-d", "LEI16@44100", "-c", "1"]


def api_key() -> Optional[str]:
    """ELEVENLABS_API_KEY from the environment, else from ~/.hermes/.env.

    The key is never logged, echoed, or included in an exception message.
    """
    key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
    if key:
        return key
    try:
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == "ELEVENLABS_API_KEY":
            value = value.strip().strip("'\"")
            return value or None
    return None


def estimate_duration(text: str) -> float:
    """Draft-mode length: word count at the narrator's measured pace."""
    return max(1.5, len((text or "").split()) / WORDS_PER_SECOND)


def _afconvert(src: Path, dest: Path) -> None:
    """Convert any AudioToolbox-readable file to 44.1 kHz mono 16-bit WAV."""
    subprocess.run(
        ["afconvert", *WAV_FORMAT, str(src), str(dest)],
        check=True,
        capture_output=True,
    )


def _say_synthesize(text: str, voice: str, aiff: Path) -> None:
    subprocess.run(
        ["say", "-v", voice, "-o", str(aiff), text],
        check=True,
        capture_output=True,
    )


def _eleven_synthesize(text: str, prev_text, next_text, voice_id: str, dest: Path) -> None:
    key = api_key()
    if not key:
        raise RuntimeError(
            "voice mode 'eleven' needs ELEVENLABS_API_KEY "
            "(environment or ~/.hermes/.env)"
        )
    settings = dict(ELEVEN_SETTINGS)
    payload = {"text": text, "model_id": ELEVEN_MODEL, "voice_settings": settings}
    # Neighbouring beats as context so each clip's intonation flows into the next.
    if prev_text:
        payload["previous_text"] = prev_text
    if next_text:
        payload["next_text"] = next_text
    request = urllib.request.Request(
        ELEVEN_URL.format(voice_id=voice_id),
        data=json.dumps(payload).encode("utf-8"),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            dest.write_bytes(response.read())
    except urllib.error.HTTPError as err:
        # Body only: never surface the request headers (they carry the key).
        raise RuntimeError(
            "ElevenLabs {}: {}".format(err.code, err.read().decode(errors="replace")[:300])
        ) from None


def _identity(voice_id: str, model, settings, text, prev_text, next_text) -> str:
    identity = [voice_id, model, settings, text, prev_text, next_text]
    blob = json.dumps(identity, sort_keys=True).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()


def wav_duration(path: Path) -> float:
    """Length of a WAV from its header (frames / framerate) — no afinfo."""
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
    return frames / float(rate) if rate else 0.0


def synthesize(
    text: str,
    mode: str,
    cache_dir: Path,
    prev_text: Optional[str] = None,
    next_text: Optional[str] = None,
    voice: Optional[str] = None,
) -> Tuple[Optional[Path], float]:
    """Return (wav_path_or_None, duration_seconds) for one beat of narration."""
    text = (text or "").strip()
    cache_dir = Path(cache_dir)
    mode = (mode or "draft").strip().lower()

    if mode == "draft":
        return None, estimate_duration(text)
    if mode not in ("say", "eleven"):
        raise ValueError("mode must be draft, say or eleven (got {!r})".format(mode))

    if mode == "eleven":
        voice_id = voice or ELEVEN_VOICE_ID
        model = ELEVEN_MODEL
        settings = dict(ELEVEN_SETTINGS)
        folder = cache_dir / voice_id
    else:
        voice_id = voice or SAY_VOICE
        model = None
        settings = None
        folder = cache_dir / "say"

    digest = _identity(voice_id, model, settings, text, prev_text, next_text)
    folder.mkdir(parents=True, exist_ok=True)
    clip = folder / "{}.wav".format(digest)
    if not clip.exists():
        partial = folder / "{}.part.wav".format(digest)
        if mode == "eleven":
            source = folder / "{}.part.mp3".format(digest)
            _eleven_synthesize(text, prev_text, next_text, voice_id, source)
        else:
            source = folder / "{}.part.aiff".format(digest)
            _say_synthesize(text, voice_id, source)
        try:
            _afconvert(source, partial)
        finally:
            source.unlink(missing_ok=True)
        os.replace(partial, clip)
    return clip, wav_duration(clip)