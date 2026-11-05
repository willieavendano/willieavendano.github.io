"""Unit tests for the screen-tutorial audio modules (stdlib only).

Run from the skill folder:

    cd .claude/skills/screen-tutorial
    python3 -m unittest discover -s tests -p 'test_audio*'

Nothing here touches the network: the one ElevenLabs test mocks
urllib.request.urlopen and the afconvert call, and checks the request body
shape plus the ~/.hermes/.env key fallback.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import audio  # noqa: E402
import narration  # noqa: E402
import srt  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_wav(path, seconds, rate=44100, channels=1, values=(1000,)):
    """Write a constant-tone 16-bit WAV (interleaved `values` per frame)."""
    path = Path(path)
    frames = int(round(seconds * rate))
    samples = array("h")
    for _ in range(frames):
        for channel in range(channels):
            samples.append(values[channel % len(values)])
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(samples.tobytes())
    return path


def read_wav(path):
    with wave.open(str(path), "rb") as wav:
        params = {
            "channels": wav.getnchannels(),
            "width": wav.getsampwidth(),
            "rate": wav.getframerate(),
            "frames": wav.getnframes(),
        }
        raw = wav.readframes(params["frames"])
    samples = array("h")
    samples.frombytes(raw)
    if array("h", [1]).tobytes()[0] == 0:  # big-endian host
        samples.byteswap()
    return params, samples


def amplitude_at(path, seconds):
    params, samples = read_wav(path)
    index = int(round(seconds * params["rate"])) * params["channels"]
    if index >= len(samples):
        return 0
    return samples[index]


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def wav(self, name, seconds, **kwargs):
        return write_wav(self.tmp / name, seconds, **kwargs)


# ---------------------------------------------------------------------------
# narration: draft estimate
# ---------------------------------------------------------------------------

class DraftModeTests(TempDirCase):
    def test_short_text_has_a_floor(self):
        path, seconds = narration.synthesize("one two three", "draft", self.tmp)
        self.assertIsNone(path)
        self.assertAlmostEqual(seconds, 1.5)

    def test_duration_scales_with_words(self):
        text = " ".join(["word"] * 29)  # 29 / 2.9 == 10 s
        path, seconds = narration.synthesize(text, "draft", self.tmp)
        self.assertIsNone(path)
        self.assertAlmostEqual(seconds, 10.0)
        self.assertAlmostEqual(narration.estimate_duration("a b c d e"), 5 / 2.9)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            narration.synthesize("hi", "telepathy", self.tmp)

    def test_draft_creates_no_cache_dir(self):
        narration.synthesize("one two three", "draft", self.tmp / "cache")
        self.assertFalse((self.tmp / "cache").exists())


@unittest.skipUnless(shutil.which("say") and shutil.which("afconvert"),
                     "macOS say/afconvert not available")
class SayModeTests(TempDirCase):
    def test_say_writes_wav_and_caches(self):
        cache = self.tmp / "cache"
        path, seconds = narration.synthesize("Cache me.", "say", cache)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        self.assertEqual(path.suffix, ".wav")
        self.assertEqual(path.parent, cache / "say")
        self.assertGreater(seconds, 0.0)

        params, _ = read_wav(path)
        self.assertEqual(params["channels"], 1)
        self.assertEqual(params["width"], 2)
        self.assertEqual(params["rate"], 44100)
        self.assertAlmostEqual(seconds, params["frames"] / 44100.0, places=6)
        self.assertEqual(list(path.parent.glob("*.part.*")), [])

        # A second call must be served from cache: no voice work at all.
        before = path.stat().st_mtime_ns
        with mock.patch.object(narration, "_say_synthesize",
                               side_effect=AssertionError("re-synthesized")):
            again, again_seconds = narration.synthesize("Cache me.", "say", cache)
        self.assertEqual(again, path)
        self.assertEqual(path.stat().st_mtime_ns, before)
        self.assertAlmostEqual(again_seconds, seconds)

    def test_voice_changes_cache_key_and_folder(self):
        cache = self.tmp / "cache"
        first, _ = narration.synthesize("Same words.", "say", cache, voice="Daniel")
        with mock.patch.object(narration, "_say_synthesize") as synth:
            synth.side_effect = lambda text, voice, aiff: write_wav(aiff, 0.2, 22050)
            second, _ = narration.synthesize("Same words.", "say", cache, voice="Samantha")
        self.assertNotEqual(first, second)
        self.assertTrue(synth.called)
        self.assertEqual(synth.call_args.args[1], "Samantha")


# ---------------------------------------------------------------------------
# audio: placement, padding, overlap, conversion
# ---------------------------------------------------------------------------

class AssembleTests(TempDirCase):
    def test_clip_lands_at_its_start_and_tail_is_padded(self):
        clip = self.wav("clip.wav", 0.5, values=(10000,))
        out = self.tmp / "track.wav"
        audio.assemble([(1.0, clip)], out, total_seconds=2.0)

        params, _ = read_wav(out)
        self.assertEqual(params["channels"], 1)
        self.assertEqual(params["width"], 2)
        self.assertEqual(params["rate"], 44100)
        self.assertEqual(params["frames"], 88200)

        self.assertEqual(amplitude_at(out, 0.5), 0)      # silence before
        self.assertEqual(amplitude_at(out, 1.25), 10000)  # clip
        self.assertEqual(amplitude_at(out, 1.6), 0)      # silence after

    def test_no_leading_silence_when_clip_starts_at_zero(self):
        clip = self.wav("clip.wav", 0.25, values=(4000,))
        out = self.tmp / "track.wav"
        audio.assemble([(0.0, clip)], out)
        self.assertEqual(amplitude_at(out, 0.0), 4000)
        self.assertAlmostEqual(audio.duration(out), 0.25, places=6)

    def test_track_is_sorted_and_unsorted_input_works(self):
        early = self.wav("early.wav", 0.2, values=(111,))
        late = self.wav("late.wav", 0.2, values=(222,))
        out = self.tmp / "track.wav"
        audio.assemble([(1.0, late), (0.2, early)], out, total_seconds=1.2)
        self.assertEqual(amplitude_at(out, 0.3), 111)
        self.assertEqual(amplitude_at(out, 1.1), 222)

    def test_overlap_truncates_earlier_clip_with_fade(self):
        first = self.wav("first.wav", 1.0, values=(1000,))
        second = self.wav("second.wav", 1.0, values=(3000,))
        out = self.tmp / "track.wav"
        audio.assemble([(0.0, first), (0.5, second)], out, total_seconds=2.0)

        self.assertEqual(amplitude_at(out, 0.4), 1000)   # before the fade
        mid_fade = amplitude_at(out, 0.49)
        self.assertGreater(mid_fade, 0)
        self.assertLess(mid_fade, 1000)                  # fading, not cut
        self.assertEqual(amplitude_at(out, 0.6), 3000)   # second clip owns it
        self.assertEqual(amplitude_at(out, 1.4), 3000)
        self.assertEqual(amplitude_at(out, 1.51), 0)     # nothing bleeds past
        self.assertAlmostEqual(audio.duration(out), 2.0, places=6)

    def test_overlap_never_mixes_two_clips(self):
        first = self.wav("first.wav", 0.8, values=(9000,))
        second = self.wav("second.wav", 0.8, values=(100,))
        out = self.tmp / "track.wav"
        audio.assemble([(0.0, first), (0.3, second)], out)
        # If they mixed, the sum would exceed either clip's amplitude.
        for t in (0.35, 0.45, 0.55, 0.7, 0.8, 1.05):
            self.assertLessEqual(abs(amplitude_at(out, t)), 9000)

    def test_stereo_is_averaged_to_mono(self):
        clip = self.wav("stereo.wav", 0.5, channels=2, values=(1000, 3000))
        out = self.tmp / "track.wav"
        audio.assemble([(0.0, clip)], out)
        params, _ = read_wav(out)
        self.assertEqual(params["channels"], 1)
        self.assertEqual(amplitude_at(out, 0.2), 2000)

    def test_low_sample_rate_is_resampled(self):
        clip = self.wav("slow.wav", 0.5, rate=22050, values=(2000,))
        out = self.tmp / "track.wav"
        audio.assemble([(0.0, clip)], out)
        params, samples = read_wav(out)
        self.assertEqual(params["rate"], 44100)
        self.assertAlmostEqual(len(samples) / 44100.0, 0.5, delta=0.001)
        self.assertEqual(amplitude_at(out, 0.1), 2000)
        self.assertEqual(amplitude_at(out, 0.4), 2000)

    def test_eight_khz_stereo_with_negative_start(self):
        clip = self.wav("tiny.wav", 0.2, rate=8000, channels=2, values=(400, 800))
        out = self.tmp / "track.wav"
        audio.assemble([(-1.0, clip)], out, total_seconds=0.25)
        self.assertEqual(amplitude_at(out, 0.05), 600)
        self.assertAlmostEqual(audio.duration(out), 0.25, places=6)

    def test_duration_reads_the_header(self):
        clip = self.wav("clip.wav", 1.234, values=(0,))
        self.assertAlmostEqual(audio.duration(clip), 1.234, delta=1.0 / 44100)


# ---------------------------------------------------------------------------
# srt: wrapping, timestamps, proportional timing
# ---------------------------------------------------------------------------

class SplitTextTests(unittest.TestCase):
    def test_short_text_is_one_subtitle(self):
        self.assertEqual(srt.split_text("one two three", 7, 2), ["one two three"])

    def test_blank_text_gives_no_subtitles(self):
        self.assertEqual(srt.split_text("   ", 7, 2), [])
        self.assertEqual(srt.split_text("", 7, 2), [])

    def test_plain_text_splits_at_the_word_budget(self):
        text = " ".join("word{}".format(i) for i in range(20))
        parts = srt.split_text(text, 7, 2)
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[0].split()), 14)
        self.assertEqual(len(parts[1].split()), 6)
        for part in parts:
            lines = part.split("\n")
            self.assertLessEqual(len(lines), 2)
            self.assertTrue(all(len(line.split()) <= 7 for line in lines))
        self.assertEqual(" ".join(part.replace("\n", " ") for part in parts).split(),
                         text.split())

    def test_break_prefers_clause_punctuation(self):
        words = ["word{}".format(i) for i in range(20)]
        words[9] = "word9,"  # comma after the tenth word, inside 7..14 window
        parts = srt.split_text(" ".join(words), 7, 2)
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[0].split()), 10)
        self.assertTrue(parts[0].split()[-1].endswith(","))

    def test_sentence_end_also_breaks(self):
        words = ["word{}".format(i) for i in range(20)]
        words[7] = "word7."
        parts = srt.split_text(" ".join(words), 7, 2)
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[0].split()), 8)

    def test_lines_are_balanced(self):
        text = "alpha beta gamma delta epsilon"  # 5 words, 7/line -> 1 line
        self.assertEqual(srt.split_text(text, 7, 2), [text])
        text10 = " ".join("w{}".format(i) for i in range(10))
        part = srt.split_text(text10, 7, 2)[0]
        self.assertEqual([len(line.split()) for line in part.split("\n")], [5, 5])


class TimestampTests(unittest.TestCase):
    def test_zero_and_rollover(self):
        self.assertEqual(srt.format_timestamp(0), "00:00:00,000")
        self.assertEqual(srt.format_timestamp(1.5), "00:00:01,500")
        self.assertEqual(srt.format_timestamp(3661.5), "01:01:01,500")
        self.assertEqual(srt.format_timestamp(59.9994), "00:00:59,999")

    def test_negative_is_clamped(self):
        self.assertEqual(srt.format_timestamp(-3), "00:00:00,000")

    def test_millisecond_rounding(self):
        self.assertEqual(srt.format_timestamp(1.9996), "00:00:02,000")
        self.assertEqual(srt.format_timestamp(0.0006), "00:00:00,001")


def parse_srt(text):
    blocks = [block for block in text.strip().split("\n\n") if block.strip()]
    cues = []
    for block in blocks:
        lines = block.split("\n")
        number = int(lines[0])
        start, end = lines[1].split(" --> ")
        cues.append((number, start, end, "\n".join(lines[2:])))
    return cues


class WriteSrtTests(TempDirCase):
    def test_proportional_split_with_gap_and_numbering(self):
        path = self.tmp / "captions.srt"
        srt.write_srt([(0.0, 10.0, "one two three four five six seven eight")],
                      path, max_words_per_line=4, max_lines=1)
        body = path.read_text(encoding="utf-8")
        self.assertTrue(body.endswith("\n"))
        cues = parse_srt(body)

        self.assertEqual([cue[0] for cue in cues], [1, 2])
        self.assertEqual(cues[0][3], "one two three four")
        self.assertEqual(cues[1][3], "five six seven eight")
        self.assertEqual(cues[0][1], "00:00:00,000")
        self.assertEqual(cues[0][2], "00:00:04,970")
        self.assertEqual(cues[1][1], "00:00:05,030")   # 60 ms gap
        self.assertEqual(cues[1][2], "00:00:10,000")

    def test_numbering_continues_across_cues(self):
        path = self.tmp / "captions.srt"
        srt.write_srt([
            (0.0, 4.0, "alpha beta gamma delta"),
            (5.0, 9.0, "epsilon zeta eta theta"),
        ], path, max_words_per_line=2, max_lines=1)
        cues = parse_srt(path.read_text(encoding="utf-8"))
        self.assertEqual([cue[0] for cue in cues], [1, 2, 3, 4])
        self.assertEqual(cues[2][1], "00:00:05,000")
        self.assertEqual(cues[3][2], "00:00:09,000")

    def test_two_lines_and_utf8(self):
        path = self.tmp / "captions.srt"
        srt.write_srt([(0.0, 6.0, "Un café déjà vu — one two three four")],
                      path, max_words_per_line=3, max_lines=2)
        body = path.read_text(encoding="utf-8")
        self.assertIn("café", body)
        first = parse_srt(body)[0]
        self.assertLessEqual(len(first[3].split("\n")), 2)
        self.assertTrue(all(len(line.split()) <= 3 for line in first[3].split("\n")))

    def test_empty_text_is_skipped(self):
        path = self.tmp / "captions.srt"
        srt.write_srt([(0.0, 1.0, "  ")], path)
        self.assertEqual(path.read_text(encoding="utf-8"), "")

    def test_very_short_cue_keeps_subtitles_ordered(self):
        path = self.tmp / "captions.srt"
        srt.write_srt([(1.0, 1.07, "one two three four five six seven eight")],
                      path, max_words_per_line=4, max_lines=1)
        cues = parse_srt(path.read_text(encoding="utf-8"))
        stamps = [cue[1] for cue in cues]
        self.assertEqual(stamps, sorted(stamps))
        self.assertEqual(cues[-1][2], "00:00:01,070")


# ---------------------------------------------------------------------------
# narration: ElevenLabs request shape + API key fallback (no network)
# ---------------------------------------------------------------------------

class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"ID3-not-really-mp3"


class ElevenLabsTests(TempDirCase):
    def run_eleven(self, text="Hello there.", voice="voice123", **kwargs):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

        def fake_afconvert(source, dest):
            self.assertEqual(Path(source).suffix, ".mp3")
            write_wav(dest, 0.25, values=(50,))

        with mock.patch.object(narration.urllib.request, "urlopen", fake_urlopen), \
                mock.patch.object(narration, "_afconvert", fake_afconvert), \
                mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key-123"}):
            path, seconds = narration.synthesize(
                text, "eleven", self.tmp / "cache", voice=voice, **kwargs)
        return captured, path, seconds

    def test_request_body_and_cache(self):
        captured, path, seconds = self.run_eleven(
            prev_text="Before that.", next_text="After that.")

        self.assertTrue(path.exists())
        self.assertEqual(path.parent.name, "voice123")
        self.assertAlmostEqual(seconds, 0.25)

        request = captured["request"]
        self.assertEqual(
            request.full_url,
            "https://api.elevenlabs.io/v1/text-to-speech/voice123"
            "?output_format=mp3_44100_128",
        )
        self.assertEqual(request.get_header("Xi-api-key"), "test-key-123")
        self.assertEqual(request.get_header("Content-type"), "application/json")

        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["text"], "Hello there.")
        self.assertEqual(payload["model_id"], narration.ELEVEN_MODEL)
        self.assertEqual(payload["voice_settings"], narration.ELEVEN_SETTINGS)
        self.assertEqual(payload["previous_text"], "Before that.")
        self.assertEqual(payload["next_text"], "After that.")

        # Temp mp3 is gone; only the cached wav remains.
        self.assertEqual(list(path.parent.glob("*.mp3")), [])
        self.assertEqual(len(list(path.parent.glob("*.wav"))), 1)

        # Second call hits the cache: no request, no conversion.
        with mock.patch.object(narration.urllib.request, "urlopen",
                               side_effect=AssertionError("cache miss")), \
                mock.patch.object(narration, "_afconvert",
                                  side_effect=AssertionError("re-converted")), \
                mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key-123"}):
            again, again_seconds = narration.synthesize(
                "Hello there.", "eleven", self.tmp / "cache", voice="voice123",
                prev_text="Before that.", next_text="After that.")
        self.assertEqual(again, path)
        self.assertAlmostEqual(again_seconds, seconds)

    def test_neighbour_context_is_optional(self):
        captured, _, _ = self.run_eleven()
        payload = json.loads(captured["request"].data.decode("utf-8"))
        self.assertNotIn("previous_text", payload)
        self.assertNotIn("next_text", payload)

    def test_missing_key_raises_without_leaking(self):
        with mock.patch.object(narration, "ENV_FILE", self.tmp / "nope.env"), \
                mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                narration.synthesize("Hello.", "eleven", self.tmp / "cache")
        self.assertIn("ELEVENLABS_API_KEY", str(ctx.exception))


class ApiKeyTests(TempDirCase):
    def test_env_var_wins(self):
        env_file = self.tmp / "voice.env"
        env_file.write_text("ELEVENLABS_API_KEY=from-file\n", encoding="utf-8")
        with mock.patch.object(narration, "ENV_FILE", env_file), \
                mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "from-env"}):
            self.assertEqual(narration.api_key(), "from-env")

    def test_hermes_env_fallback_parses_key_value_lines(self):
        env_file = self.tmp / "voice.env"
        env_file.write_text(
            "# my keys\nOTHER=whatever\nELEVENLABS_API_KEY = 'abc123'\n",
            encoding="utf-8",
        )
        with mock.patch.object(narration, "ENV_FILE", env_file), \
                mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(narration.api_key(), "abc123")

    def test_missing_everywhere_returns_none(self):
        with mock.patch.object(narration, "ENV_FILE", self.tmp / "absent.env"), \
                mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(narration.api_key())


if __name__ == "__main__":
    unittest.main()