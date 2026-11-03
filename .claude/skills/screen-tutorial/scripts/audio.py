"""
audio.py — assemble one narration track from per-scene WAVs
==========================================================

The recorder can play clips live for a human watching, but the exported MP4
never trusts that timing: after the take, the narration track is rebuilt as a
single 44.1 kHz mono 16-bit WAV by placing each scene's clip at its logged
start (script-format.md, "Timing model", step 3). The MP4 is exported with
`--audio track.wav --audio-mode replace`, so sync is exact regardless of what
happened on screen.

Pure stdlib: `wave` plus `array`. There is no ffmpeg on the school Macs, so
stereo→mono and sample-rate conversion are done here. Narration is speech, not
music, so linear interpolation is plenty; and afconvert handles the final
AAC encode for the share copy.

Inputs are expected to be 16-bit PCM WAVs: mono or stereo, any rate ≥ 8 kHz.
Overlapping clips are never allowed to mix — a clip that would run into the
next one's start is truncated with a 20 ms fade so the cut is not a click.
"""

from __future__ import annotations

import subprocess
import wave
from array import array
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

SAMPLE_RATE = 44100
SAMPLE_WIDTH = 2  # bytes; 16-bit PCM
CHANNELS = 1
FADE_SECONDS = 0.020


def duration(wav_path: Path) -> float:
    """Seconds of audio, straight from the WAV header."""
    with wave.open(str(wav_path), "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
    return frames / float(rate) if rate else 0.0


def _resample(samples: array, rate_in: int) -> array:
    """Linear-interpolation resample to SAMPLE_RATE."""
    if rate_in == SAMPLE_RATE or not samples:
        return samples
    out_len = int(round(len(samples) * SAMPLE_RATE / float(rate_in)))
    if out_len <= 0:
        return array("h")
    out = array("h", bytes(SAMPLE_WIDTH * out_len))
    ratio = rate_in / float(SAMPLE_RATE)
    last = len(samples) - 1
    for i in range(out_len):
        pos = i * ratio
        base = int(pos)
        if base >= last:
            out[i] = samples[last]
            continue
        frac = pos - base
        out[i] = int(round(samples[base] + (samples[base + 1] - samples[base]) * frac))
    return out


def _read_mono(wav_path: Path) -> array:
    """Read a 16-bit WAV as mono int16 samples at SAMPLE_RATE."""
    with wave.open(str(wav_path), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.getnframes()
        raw = wav.readframes(frames)
    if width != SAMPLE_WIDTH:
        raise ValueError("{}: expected 16-bit PCM, got {}-bit".format(wav_path, width * 8))
    samples = array("h")
    samples.frombytes(raw)
    if array("h", [1]).tobytes()[0] == 0:  # big-endian host
        samples.byteswap()

    if channels > 1:
        mono = array("h", bytes(SAMPLE_WIDTH * frames))
        for i in range(frames):
            total = 0
            for ch in range(channels):
                total += samples[i * channels + ch]
            mono[i] = int(round(total / float(channels)))
        samples = mono
    return _resample(samples, rate)


def _fade_out(segment: array, seconds: float = FADE_SECONDS) -> array:
    """Linear fade to zero over the last `seconds` of a truncated clip."""
    count = min(len(segment), int(round(seconds * SAMPLE_RATE)))
    if count <= 0:
        return segment
    start = len(segment) - count
    for i in range(count):
        gain = 1.0 - (i + 1) / float(count)
        idx = start + i
        segment[idx] = int(segment[idx] * gain)
    return segment


def assemble(
    track: Sequence[Tuple[float, Path]],
    out_wav: Path,
    total_seconds: Optional[float] = None,
) -> Path:
    """Place each clip at its start time in one mono 44.1 kHz WAV.

    track: [(start_seconds, wav_path), ...]; sorted here, so callers need not.
    total_seconds: pad the tail (and clip anything past it) to this length.
    """
    out_wav = Path(out_wav)
    clips: List[Tuple[float, array]] = [
        (max(0.0, float(start)), _read_mono(Path(path)))
        for start, path in sorted(track, key=lambda item: float(item[0]))
    ]

    needed = 0
    for start, samples in clips:
        needed = max(needed, int(round(start * SAMPLE_RATE)) + len(samples))
    total = needed
    if total_seconds is not None:
        total = max(total, int(round(float(total_seconds) * SAMPLE_RATE)))

    out = array("h", bytes(SAMPLE_WIDTH * total))
    for i, (start, samples) in enumerate(clips):
        offset = int(round(start * SAMPLE_RATE))
        if offset >= total:
            continue
        limit = len(samples)
        if i + 1 < len(clips):
            next_offset = int(round(clips[i + 1][0] * SAMPLE_RATE))
            limit = min(limit, max(0, next_offset - offset))
        limit = min(limit, total - offset)
        segment = samples[:limit]
        if limit < len(samples):
            segment = _fade_out(segment)
        out[offset:offset + len(segment)] = segment

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(SAMPLE_WIDTH)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(out.tobytes())
    return out_wav


def to_m4a(wav_path: Path, out: Path) -> Path:
    """AAC 128 kbps .m4a via the system afconvert (the share/e-mail copy)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["afconvert", "-f", "m4af", "-d", "aac", "-b", "128000", str(wav_path), str(out)],
        check=True,
        capture_output=True,
    )
    return out