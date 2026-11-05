#!/usr/bin/env python3
"""
listen_check.py - did the narrator actually say the words?
===========================================================

After ElevenLabs has synthesized a lesson, transcribe each clip with
whisper.cpp and compare what the voice said with what the script asked for.
This is a *listening* test, not a grammar test: it catches a dropped word, a
garbled phrase, a delivery tag spoken aloud ("[dry] ..."), letters read as a
word (or the reverse), and wrong numbers.

Two pipelines are supported:

    listen_check.py tutorial <timeline.json> [--report out.json] [--threshold 0.25]
    listen_check.py manim <scene_file.py> [<scene_file.py> ...] [...]

Tutorial clips are the WAVs named by `scenes[].clip` in a build's
`<code>.timeline.json`; the intended text is `scenes[].caption`.

Manim clips are cached on the Mac Mini as

    ~/render/phy-videos/narration_cache/<voiceId>/<sha1[:16]>.mp3

and the intended text is the SCRIPT dict in each `videos/manim/phy_*.py`.
A beat's hash is repeated exactly from `cushman.narration_clip()`:

    sha1(json.dumps([voice, model, settings, direction, text, prev, next],
                    sort_keys=True))[:16]

The whisper.cpp model, ffmpeg, and the clips themselves live on the Mini, so
transcription is done there. Everything is batched into a single ssh session:
local clips travel in a tar on ssh's stdin and the remote script loops over all
of them. Nothing is installed on this Mac.

Exit status: 0 if every clip is clean, 1 if any clip is flagged, 2 if the
configuration or the remote transcription failed.

Python 3.9 standard library only.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import io
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

DEFAULT_HOST = os.environ.get("LISTEN_CHECK_HOST", "luna@100.121.78.28")
DEFAULT_REMOTE_CACHE = os.environ.get(
    "LISTEN_CHECK_REMOTE_CACHE", "$HOME/render/phy-videos/narration_cache"
)
SSH_TIMEOUT = float(os.environ.get("LISTEN_CHECK_TIMEOUT", "1800"))

WHISPER_BIN = "/opt/homebrew/bin/whisper-cli"
FFMPEG_BIN = "/opt/homebrew/bin/ffmpeg"
WHISPER_MODEL = "$HOME/whisper/ggml-small.en.bin"


# ---------------------------------------------------------------------------
# Numbers: whisper writes "651.84", the scripts write "six fifty one eighty four"
# ---------------------------------------------------------------------------
ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
SMALL = dict(ONES)
SMALL.update(TENS)
BIG_SCALES = {"thousand": 1000, "million": 1000000, "billion": 1000000000}

# Ordinals are common in dates ("November twelfth", "12th").
ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
    "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
    "nineteenth": 19, "twentieth": 20, "thirtieth": 30, "fortieth": 40,
    "fiftieth": 50, "sixtieth": 60, "seventieth": 70, "eightieth": 80,
    "ninetieth": 90, "hundredth": 100, "thousandth": 1000,
}
NUMBER_WORDS = set(SMALL) | set(ORDINALS) | set(BIG_SCALES) | {"hundred", "oh"}
CURRENCY_WORDS = {"dollar", "dollars", "cent", "cents"}


def _int_to_words(n: int) -> str:
    """Cardinal words for a non-negative integer (the usual short scale)."""
    n = int(n)
    if n < 0:
        return "negative " + _int_to_words(-n)
    if n < 20:
        return next(k for k, v in ONES.items() if v == n)
    if n < 100:
        tens, rest = divmod(n, 10)
        word = next(k for k, v in TENS.items() if v == tens * 10)
        if rest:
            word += " " + _int_to_words(rest)
        return word
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        word = _int_to_words(hundreds) + " hundred"
        if rest:
            word += " " + _int_to_words(rest)
        return word
    for scale, name in (
        (1000000000, "billion"), (1000000, "million"), (1000, "thousand")
    ):
        if n >= scale:
            head, rest = divmod(n, scale)
            word = _int_to_words(head) + " " + name
            if rest:
                word += " " + _int_to_words(rest)
            return word
    return str(n)


def _digits_to_words(digits: str) -> str:
    return " ".join(
        next(k for k, v in ONES.items() if v == int(d)) for d in digits
    )


def number_to_words(value) -> str:
    """Spell a number the way the scripts write it.

    >>> number_to_words(651.84)
    'six hundred fifty one point eight four'
    >>> number_to_words("4.5")
    'four point five'
    >>> number_to_words("$16,000")
    'sixteen thousand'
    """
    text = str(value).strip().replace("$", "").replace("%", "").replace(",", "")
    text = text.replace("\u2212", "-")
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    if not text:
        return ""
    if text.startswith("."):
        text = "0" + text
    if "." in text:
        whole, frac = text.split(".", 1)
        whole_words = _int_to_words(int(whole or 0))
        frac_words = _digits_to_words(re.sub(r"\D", "", frac))
        result = whole_words + (" point " + frac_words if frac_words else "")
    else:
        digits = re.sub(r"\D", "", text)
        if not digits:
            return ""
        result = _int_to_words(int(digits))
    return ("negative " + result) if negative else result


def money_to_words(value) -> str:
    """Spell a dollar amount: '$16,000' -> 'sixteen thousand dollars'."""
    text = str(value).strip().replace("$", "").replace(",", "")
    text = text.replace("\u2212", "-")
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    if text.startswith("."):
        text = "0" + text
    if "." in text:
        whole, frac = text.split(".", 1)
    else:
        whole, frac = text, ""
    dollars = int(whole or 0)
    cents = int((frac + "00")[:2]) if frac else 0
    parts = []
    if dollars or not cents:
        parts.append(number_to_words(dollars) + (" dollar" if dollars == 1 else " dollars"))
    if cents:
        parts.append(number_to_words(cents) + (" cent" if cents == 1 else " cents"))
    result = " and ".join(parts)
    return ("negative " + result) if negative else result


# ---------------------------------------------------------------------------
# Tokenisation and the comparison form
# ---------------------------------------------------------------------------
# Spoken initialisms that should survive a letter-by-letter spelling. This is
# deliberately narrow: "if" must NOT be in here, so "if" vs "i f" is flagged.
ACRONYMS = {
    "apy", "apr", "pmt", "npv", "irr", "fv", "pv", "kdea", "kde", "csm",
    "hysa", "csv", "tsv", "pdf", "url", "api", "html", "http", "https",
    "roi", "gdp", "usb", "min", "max", "sum", "avg",
}

# Words that are directions to the voice, not content. If one shows up in the
# transcript and the script never asked for it, the tag was spoken aloud.
TAG_WORDS = {
    "dry", "deadpan", "wry", "understated", "whispering", "whisper",
    "monotone", "sarcastic", "sarcastically", "playful", "playfully",
    "cheerfully", "flatly", "excitedly", "matter-of-fact",
    "faintly", "amused",
}

_TOKEN_RE = re.compile(
    r"""
      (?P<comma_num>\d{1,3}(?:,\d{3})+(?:\.\d+)?)
    | (?P<num>\d+(?:\.\d+)?|\.\d+)
    | (?P<word>[A-Za-z]+(?:['\u2019][A-Za-z]+)*)
    | (?P<symbol>[%$])
    """,
    re.VERBOSE,
)
_BRACKET_RE = re.compile(r"\[([^\]]{1,80})\]|\(([^)]{1,80})\)|\{([^}]{1,80})\}")
_TAG_STRIP_RE = re.compile(r"\[[^\]]*\]|\{[^}]*\}")


def _literal_skeleton(text: str) -> str:
    """Digits without punctuation: '651.84' -> '65184', '$16,000' -> '16000'."""
    clean = text.replace(",", "").replace("$", "").replace("%", "").strip()
    if clean.startswith("."):
        clean = "0" + clean
    if "." in clean:
        whole, frac = clean.split(".", 1)
    else:
        whole, frac = clean, ""
    whole = str(int(whole or "0"))
    return whole + re.sub(r"\D", "", frac)


def _integer_groups_to_skeleton(words: Sequence[str]) -> str:
    """Turn spoken number words into a digit skeleton.

    The scripts use the spoken-money shorthand ("six fifty one eighty four"),
    so groups are concatenated rather than added: [651, 84] -> "65184", which
    is exactly what "$651.84" becomes.
    """
    groups: List[str] = []
    big = 0
    cur = 0
    seen = False

    def flush():
        nonlocal big, cur
        groups.append(str(big + cur))
        big = 0
        cur = 0

    for word in words:
        if word.startswith("#"):
            # A literal number from whisper, already reduced to digits.
            seen = True
            groups.append(_literal_skeleton(word[1:]))
            continue
        if word == "hundred":
            seen = True
            cur = (cur or 1) * 100
            continue
        if word in BIG_SCALES:
            seen = True
            scale = BIG_SCALES[word]
            big += (cur or 1) * scale
            cur = 0
            continue
        if word == "a":
            value = 1
        elif word == "oh":
            value = 0
        elif word in ORDINALS:
            value = ORDINALS[word]
        else:
            value = SMALL.get(word)
        if value is None:
            continue
        seen = True

        if value < 10:
            if cur == 0:
                cur = value
            elif cur >= 100 and cur % 10 == 0:
                cur += value
            elif 10 <= cur < 100 and cur % 10 == 0:
                cur += value
            else:
                flush()
                cur = value
        elif value < 100:
            if cur == 0:
                cur = value
            elif cur < 10:
                # "six fifty one" means six hundred fifty one.
                cur = cur * 100 + value
            elif cur >= 100 and cur % 100 == 0:
                cur += value
            else:
                flush()
                cur = value
        else:
            # An explicit scale word should have been handled above, but a
            # bare "hundred" value reaching here is harmless.
            if cur == 0:
                cur = value
            else:
                flush()
                cur = value

    if seen and (big or cur or not groups):
        groups.append(str(big + cur))
    if not groups:
        return ""
    return "".join(groups)


def _fraction_to_skeleton(words: Sequence[str]) -> str:
    digits: List[str] = []
    index = 0
    while index < len(words):
        word = words[index]
        if word.startswith("#"):
            digits.append(_literal_skeleton(word[1:]))
            index += 1
            continue
        if word in TENS and index + 1 < len(words) and words[index + 1] in ONES:
            unit = ONES[words[index + 1]]
            if unit < 10:
                digits.append(str(TENS[word] + unit))
                index += 2
                continue
        if word == "oh":
            digits.append("0")
        elif word in ORDINALS:
            digits.append(str(ORDINALS[word]))
        elif word in SMALL:
            digits.append(str(SMALL[word]))
        index += 1
    return "".join(digits)


def _run_to_skeleton(words: Sequence[str]) -> Tuple[str, bool]:
    """Return (digit skeleton, has_cents) for a run of number words."""
    has_cents = any(w in ("cent", "cents") for w in words)
    core = [w for w in words if w not in CURRENCY_WORDS and w != "and"]
    if "point" in core:
        split = core.index("point")
        whole_words, frac_words = core[:split], core[split + 1:]
    else:
        whole_words, frac_words = core, []
    whole = _integer_groups_to_skeleton(whole_words)
    frac = _fraction_to_skeleton(frac_words)
    if frac:
        if not whole:
            whole = "0"
        return whole + frac, has_cents
    return whole, has_cents


def _is_number_word(word: str) -> bool:
    return word in NUMBER_WORDS or word in CURRENCY_WORDS


def _next_meaningful(items: Sequence[Tuple[str, str]], index: int) -> Optional[str]:
    for kind, value in items[index + 1:]:
        if kind == "symbol":
            continue
        return value.lower()
    return None


def tokenize(text: str, join: bool = True) -> List[str]:
    """Lowercase, strip punctuation, and turn every number into a digit skeleton.

    With join=True (the comparison form), letter runs that spell a known
    initialism are joined ("a p y" -> "apy") and cell references are joined
    ("b five" -> "b5"). With join=False, single letters stay separate so the
    letters-vs-word check can see them.
    """
    text = (text or "").replace("&", " and ")
    # A leading minus is spoken as "negative"; the scripts write it as a word.
    text = re.sub(r"(?<![\w])[-\u2212](?=\d)", " negative ", text)
    matches = list(_TOKEN_RE.finditer(text))
    items: List[Tuple[str, str]] = []
    gaps: List[bool] = []
    previous_end = 0
    previous_kind = ""
    for match in matches:
        kind = match.lastgroup or ""
        value = match.group(0)
        gap = text[previous_end:match.start()].strip()
        # A hyphen between words keeps "twenty-four" in one number;
        # punctuation between two numbers separates them ("24: 4,302").
        word_hyphen = (
            gap in ("-", "\u2013")
            and previous_kind == "word"
            and kind == "word"
        )
        gaps.append(bool(gap) and not word_hyphen)
        items.append((kind, value))
        previous_end = match.end()
        previous_kind = kind

    tokens: List[str] = []
    run: List[str] = []

    def flush():
        nonlocal run
        if not run:
            return
        skeleton, has_cents = _run_to_skeleton(run)
        if skeleton:
            if has_cents and not any(w in ("dollar", "dollars") for w in run):
                if len(skeleton) <= 2:
                    skeleton = "0" + skeleton.zfill(2)
            tokens.append(skeleton)
        run = []

    index = 0
    while index < len(items):
        if gaps[index]:
            flush()
        kind, raw = items[index]
        if kind == "symbol":
            if raw == "%":
                flush()
                tokens.append("percent")
            else:  # "$"
                flush()
            index += 1
            continue

        if kind in ("comma_num", "num"):
            # A literal starts its own group unless it is part of a money run
            # ("4 dollars and 84 cents") or a decimal ("four point 5").
            if run and not any(w in CURRENCY_WORDS for w in run) and run[-1] != "point":
                flush()
            run.append("#" + raw)
            index += 1
            # A currency word directly after the literal belongs to the run.
            if index < len(items) and items[index][0] == "word":
                word = items[index][1].lower()
                if word in CURRENCY_WORDS:
                    run.append(word)
                    index += 1
            # Skip an ordinal suffix token.
            if index < len(items) and items[index][0] == "word" and \
                    items[index][1].lower() in ("st", "nd", "rd", "th"):
                index += 1
            continue

        word = raw.lower().replace("'", "").replace("\u2019", "")
        if word in ("st", "nd", "rd", "th") and tokens:
            index += 1
            continue

        if word == "point" and run:
            run.append(word)
            index += 1
            continue
        if word == "oh" and run:
            run.append(word)
            index += 1
            continue
        if word == "a":
            # "a hundred" / "a dollar eighty four" mean one of something; the
            # article in "a car" or the column letter in "a eleven" is a word.
            nxt = _next_meaningful(items, index)
            numeric_a = nxt in (
                "hundred", "thousand", "million", "billion",
                "dollar", "dollars", "cent", "cents",
            )
            if numeric_a:
                run.append(word)
                index += 1
                continue
            flush()
            tokens.append("a")
            index += 1
            continue
        if word in NUMBER_WORDS and word != "oh":
            run.append(word)
            index += 1
            continue
        if word in CURRENCY_WORDS:
            nxt = _next_meaningful(items, index)
            if run or (nxt and _is_number_word(nxt)):
                run.append(word)
                index += 1
                continue
        if word == "and" and run:
            nxt = _next_meaningful(items, index)
            if nxt and (
                _is_number_word(nxt)
                or nxt in CURRENCY_WORDS
                or re.fullmatch(r"\d+(?:\.\d+)?", nxt)
            ):
                run.append(word)
                index += 1
                continue

        flush()
        tokens.append(word)
        index += 1

    flush()
    return _join_tokens(tokens) if join else tokens


def _is_letter(token: str) -> bool:
    return len(token) == 1 and token.isalpha()


def _join_tokens(tokens: Sequence[str]) -> List[str]:
    """Join known initialisms and cell references after number conversion."""
    out: List[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if _is_letter(token):
            end = index
            while end < len(tokens) and _is_letter(tokens[end]):
                end += 1
            run = list(tokens[index:end])
            joined = "".join(run)
            if len(run) >= 2 and joined in ACRONYMS:
                out.append(joined)
                index = end
                continue
            if len(run) == 1 and end < len(tokens) and tokens[end].isdigit():
                out.append(run[0] + tokens[end])
                index = end + 1
                continue
            out.extend(run)
            index = end
            continue
        out.append(token)
        index += 1
    return out


def normalize_text(text: str, join: bool = True) -> str:
    return " ".join(tokenize(text, join=join))


def _strip_delivery_tags(text: str) -> str:
    return _TAG_STRIP_RE.sub(" ", text or "")


# ---------------------------------------------------------------------------
# WER, alignment, and the per-clip verdict
# ---------------------------------------------------------------------------
def edit_distance(reference: Sequence[str], hypothesis: Sequence[str]) -> int:
    """Plain Levenshtein distance with unit substitution cost."""
    if not reference:
        return len(hypothesis)
    if not hypothesis:
        return len(reference)
    previous = list(range(len(hypothesis) + 1))
    for i, ref_token in enumerate(reference, 1):
        current = [i]
        for j, hyp_token in enumerate(hypothesis, 1):
            cost = 0 if ref_token == hyp_token else 1
            current.append(min(
                previous[j] + 1,          # deletion
                current[j - 1] + 1,       # insertion
                previous[j - 1] + cost,   # substitution
            ))
        previous = current
    return previous[-1]


def word_error_rate(reference: Sequence[str], hypothesis: Sequence[str]) -> float:
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return edit_distance(reference, hypothesis) / float(len(reference))


def _short(tokens: Sequence[str], limit: int = 5) -> str:
    if not tokens:
        return "(nothing)"
    shown = list(tokens[:limit])
    text = " ".join(shown)
    if len(tokens) > limit:
        text += " ..."
    return text


def first_difference(reference: Sequence[str], hypothesis: Sequence[str]) -> str:
    """A compact description of the first place the two token streams diverge."""
    if list(reference) == list(hypothesis):
        return ""
    matcher = difflib.SequenceMatcher(a=list(reference), b=list(hypothesis), autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        ref = list(reference[i1:i2])
        hyp = list(hypothesis[j1:j2])
        if tag == "replace":
            return "expected '%s' got '%s'" % (_short(ref), _short(hyp))
        if tag == "delete":
            return "missing '%s'" % _short(ref)
        return "extra '%s'" % _short(hyp)
    return ""


def _letter_mismatches(
    reference: Sequence[str], hypothesis: Sequence[str]
) -> List[str]:
    """Find 'if' vs 'i f' / 'I.F.' mismatches, ignoring real initialisms."""
    def runs(tokens):
        result: Set[str] = set()
        index = 0
        while index < len(tokens):
            if _is_letter(tokens[index]):
                end = index
                while end < len(tokens) and _is_letter(tokens[end]):
                    end += 1
                if end - index >= 2:
                    joined = "".join(tokens[index:end])
                    if joined not in ACRONYMS:
                        result.add(joined)
                index = end
            else:
                index += 1
        return result

    ref_runs = runs(reference)
    hyp_runs = runs(hypothesis)
    flags = []
    # Only flag the direction the scripts care about: a word in the script
    # that whisper rendered as separate letters ("if" -> "i f"). If the
    # script itself spells letters ("v x"), whisper joining them is fine.
    for word in sorted(hyp_runs - ref_runs):
        if word in reference:
            flags.append("letters: transcript spelled '%s' as letters" % word)
    return flags


def _bracketed_tags(transcript: str) -> List[str]:
    found = []
    for match in _BRACKET_RE.finditer(transcript or ""):
        content = next(group for group in match.groups() if group is not None)
        content = content.strip()
        if not content or len(content) > 40:
            continue
        if re.search(r"[.!?]", content):
            continue
        if not re.search(r"[A-Za-z]", content):
            continue
        found.append(content)
    return found


def _tag_flags(transcript: str, intended_tokens: Set[str]) -> List[str]:
    flags: List[str] = []
    intended_words = set(intended_tokens)
    bracketed_words: Set[str] = set()
    for content in _bracketed_tags(transcript):
        content_words = set(tokenize(content, join=False))
        if content_words and content_words.issubset(intended_words):
            continue
        bracketed_words.update(content_words)
        flags.append("tag: [%s]" % content)
    for word in sorted(TAG_WORDS):
        if word in bracketed_words:
            continue
        if re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % re.escape(word), transcript or "", re.I):
            if word not in intended_words:
                flags.append("tag: '%s' spoken" % word)
    # De-duplicate in a stable order.
    seen = set()
    unique = []
    for flag in flags:
        if flag not in seen:
            seen.add(flag)
            unique.append(flag)
    return unique


def analyze_clip(
    clip_id: str,
    intended: str,
    transcript: Optional[str],
    threshold: float,
    clip_path: str = "",
    error: Optional[str] = None,
) -> Dict:
    """Compare one intended line with one transcript and return a report row."""
    intended_for_compare = _strip_delivery_tags(intended or "")
    ref = tokenize(intended_for_compare, join=True)
    hyp = tokenize(transcript or "", join=True)
    ref_raw = tokenize(intended_for_compare, join=False)
    hyp_raw = tokenize(transcript or "", join=False)

    flags: List[str] = []
    if error:
        return {
            "id": clip_id,
            "clip": clip_path,
            "intended": intended,
            "transcript": transcript,
            "wer": None,
            "flags": ["error: %s" % error],
            "flagged": True,
            "first_difference": "",
            "tags": [],
            "letter_mismatches": [],
            "missing_numbers": [],
            "error": error,
        }

    wer = word_error_rate(ref, hyp)
    if not (transcript or "").strip():
        flags.append("empty transcript")
    if wer > threshold:
        flags.append("wer %.3f > %.2f" % (wer, threshold))

    tag_flags = _tag_flags(transcript or "", set(ref))
    flags.extend(tag_flags)

    letter_flags = _letter_mismatches(ref_raw, hyp_raw)
    flags.extend(letter_flags)

    intended_numbers = []
    for token in ref:
        if token.isdigit() and token not in intended_numbers:
            intended_numbers.append(token)
    transcript_numbers = {token for token in hyp if token.isdigit()}
    missing_numbers = [n for n in intended_numbers if n not in transcript_numbers]
    for number in missing_numbers:
        flags.append("number missing: %s" % number)

    if letter_flags:
        difference = first_difference(ref_raw, hyp_raw)
    elif wer == 0.0:
        difference = ""
    else:
        difference = first_difference(ref, hyp)

    return {
        "id": clip_id,
        "clip": clip_path,
        "intended": intended,
        "transcript": transcript,
        "wer": round(wer, 4),
        "flags": flags,
        "flagged": bool(flags),
        "first_difference": difference,
        "tags": tag_flags,
        "letter_mismatches": letter_flags,
        "missing_numbers": missing_numbers,
        "error": error,
    }


# ---------------------------------------------------------------------------
# Reading the two pipelines
# ---------------------------------------------------------------------------
@dataclass
class CheckItem:
    id: str
    intended: str
    local_path: Optional[Path] = None
    remote_path: Optional[str] = None
    display_path: str = ""
    pre_error: Optional[str] = None
    job_index: Optional[int] = None


@dataclass
class Job:
    index: int
    local_path: Optional[Path]
    remote_path: Optional[str]
    display_path: str


def load_tutorial_items(timeline_path: Path) -> List[CheckItem]:
    data = json.loads(Path(timeline_path).read_text(encoding="utf-8"))
    scenes = data.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("%s: no `scenes` list" % timeline_path)
    base = Path(timeline_path).resolve().parent
    items: List[CheckItem] = []
    for number, scene in enumerate(scenes, 1):
        clip_id = str(scene.get("id") or "scene-%d" % number)
        intended = scene.get("caption") or scene.get("say") or ""
        clip = scene.get("clip")
        if not intended:
            items.append(CheckItem(
                id=clip_id, intended="", display_path=clip or "",
                pre_error="no caption/say text in timeline",
            ))
            continue
        if not clip:
            items.append(CheckItem(
                id=clip_id, intended=intended, display_path="",
                pre_error="no clip in timeline (a draft build has no audio)",
            ))
            continue
        path = Path(clip)
        if not path.is_absolute():
            path = base / path
        if not path.is_file():
            items.append(CheckItem(
                id=clip_id, intended=intended, display_path=str(path),
                pre_error="clip not found: %s" % path,
            ))
            continue
        items.append(CheckItem(
            id=clip_id, intended=intended, local_path=path,
            display_path=str(path),
        ))
    return items


@dataclass
class SceneScript:
    path: Path
    class_name: str
    video_code: str
    beats: List[Tuple[str, str]] = field(default_factory=list)


def _resolve_script_node(
    node: ast.AST, module_assignments: Dict[str, ast.AST]
) -> Dict[str, str]:
    if isinstance(node, ast.Name) and node.id in module_assignments:
        return _resolve_script_node(module_assignments[node.id], module_assignments)
    value = ast.literal_eval(node)
    if not isinstance(value, dict):
        raise ValueError("SCRIPT is not a dict")
    script: Dict[str, str] = {}
    for key, text in value.items():
        if not isinstance(key, str) or not isinstance(text, str):
            raise ValueError("SCRIPT keys and values must be strings")
        script[key] = text
    return script


def parse_scene_file(path: Path) -> List[SceneScript]:
    """Parse `class Foo(NarratedScene): SCRIPT = {...}` with ast, never import."""
    path = Path(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module_assignments: Dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module_assignments[target.id] = node.value

    scenes: List[SceneScript] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        script_node = None
        video_code = ""
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "SCRIPT":
                        script_node = item.value
                    if isinstance(target, ast.Name) and target.id == "VIDEO_CODE":
                        try:
                            video_code = str(ast.literal_eval(item.value))
                        except (ValueError, SyntaxError):
                            video_code = ""
        if script_node is None:
            continue
        script = _resolve_script_node(script_node, module_assignments)
        scenes.append(SceneScript(
            path=path,
            class_name=node.name,
            video_code=video_code,
            beats=list(script.items()),
        ))
    return scenes


@dataclass
class ManimConfig:
    voice_id: str
    model: str
    settings: Dict
    direction: str
    identity_has_direction: bool
    cushman_path: Path
    voice_env: Dict[str, str]


class ConfigError(RuntimeError):
    pass


def read_env_file(path: Path) -> Dict[str, str]:
    """Read KEY=VALUE lines; matching render.sh's `set -a; . voice.env`."""
    result: Dict[str, str] = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return result
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        result[key] = value
    return result


def _is_os_environ(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _eval_ast(node: ast.AST, env: Dict[str, str]):
    """Evaluate the tiny subset of Python used in cushman.py's config."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise ConfigError("unknown name %r in cushman.py" % node.id)
    if isinstance(node, ast.Dict):
        return {
            _eval_ast(key, env): _eval_ast(value, env)
            for key, value in zip(node.keys, node.values)
        }
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval_ast(element, env) for element in node.elts]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_ast(node.operand, env)
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name) and func.id in ("float", "int", "str", "bool"):
            value = _eval_ast(node.args[0], env) if node.args else ""
            return {"float": float, "int": int, "str": str, "bool": bool}[func.id](value)
        if isinstance(func, ast.Attribute):
            if func.attr == "get" and _is_os_environ(func.value):
                key = _eval_ast(node.args[0], env) if node.args else ""
                default = _eval_ast(node.args[1], env) if len(node.args) > 1 else None
                return env.get(str(key), default)
            if func.attr in ("strip", "lower", "upper"):
                value = _eval_ast(func.value, env)
                if func.attr == "strip":
                    return str(value).strip()
                if func.attr == "lower":
                    return str(value).lower()
                return str(value).upper()
        raise ConfigError("cannot evaluate call in cushman.py")
    if _is_os_environ(node):
        return env
    raise ConfigError("cannot evaluate %s in cushman.py" % type(node).__name__)


def load_manim_config(manim_dir: Path) -> ManimConfig:
    manim_dir = Path(manim_dir)
    cushman_path = manim_dir / "cushman.py"
    voice_env_path = manim_dir / "voice.env"
    if not cushman_path.is_file():
        raise ConfigError("cushman.py not found in %s" % manim_dir)
    voice_env = read_env_file(voice_env_path)
    env = dict(os.environ)
    env.update(voice_env)  # render.sh sources voice.env after the ambient env

    tree = ast.parse(cushman_path.read_text(encoding="utf-8"), filename=str(cushman_path))
    module_assignments: Dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module_assignments[target.id] = node.value

    def assignment(name: str):
        return module_assignments.get(name)

    def value_of(name: str, fallback=None):
        node = assignment(name)
        if node is None:
            return fallback
        try:
            return _eval_ast(node, env)
        except ConfigError:
            return fallback

    settings_node = assignment("ELEVEN_SETTINGS")
    if settings_node is None:
        raise ConfigError("ELEVEN_SETTINGS not found in cushman.py")
    settings = _eval_ast(settings_node, env)
    if not isinstance(settings, dict):
        raise ConfigError("ELEVEN_SETTINGS is not a dict in cushman.py")

    voice_id = str(env.get("ELEVEN_VOICE_ID") or value_of("ELEVEN_VOICE_ID") or "")
    model = str(env.get("ELEVEN_MODEL") or value_of("ELEVEN_MODEL") or "")
    direction = str(env.get("ELEVEN_DIRECTION", "")).strip()
    if "ELEVEN_DIRECTION" not in env:
        direction = str(value_of("ELEVEN_DIRECTION", "") or "").strip()
    if not voice_id or not model:
        raise ConfigError("ELEVEN_VOICE_ID / ELEVEN_MODEL not found in voice.env or cushman.py")

    # Current cushman.py identity is [voice, model, settings, direction, text,
    # prev, next]. Detect whether the direction is part of it, so an older
    # cushman.py without the prefix still maps correctly.
    identity_has_direction = True
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "narration_clip":
            candidates = []
            for inner in ast.walk(node):
                if isinstance(inner, ast.Assign):
                    for target in inner.targets:
                        if isinstance(target, ast.Name) and target.id == "identity":
                            if isinstance(inner.value, (ast.List, ast.Tuple)):
                                candidates.append(inner.value.elts)
            # There are two identities: the ElevenLabs one and the `say` one.
            # Pick the ElevenLabs list (it names ELEVEN_MODEL).
            for elements in candidates:
                names = {
                    element.id for element in elements
                    if isinstance(element, ast.Name)
                }
                if "ELEVEN_MODEL" in names:
                    identity_has_direction = "ELEVEN_DIRECTION" in names
                    break
            break

    return ManimConfig(
        voice_id=voice_id,
        model=model,
        settings=settings,
        direction=direction,
        identity_has_direction=identity_has_direction,
        cushman_path=cushman_path,
        voice_env=voice_env,
    )


def manim_identity_hash(
    text: str,
    prev_text: Optional[str],
    next_text: Optional[str],
    config: ManimConfig,
) -> str:
    """sha1(json.dumps(identity, sort_keys=True))[:16], exactly as cushman.py."""
    identity = [config.voice_id, config.model, config.settings]
    if config.identity_has_direction:
        identity.append(config.direction)
    identity.extend([text, prev_text, next_text])
    blob = json.dumps(identity, sort_keys=True).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()[:16]


def find_manim_dir(scene_files: Sequence[Path]) -> Path:
    for scene_file in scene_files:
        current = Path(scene_file).resolve().parent
        for _ in range(8):
            if (current / "cushman.py").is_file():
                return current
            if current.parent == current:
                break
            current = current.parent
    raise ConfigError(
        "cannot find cushman.py near: %s" % ", ".join(str(p) for p in scene_files)
    )


def load_manim_items(
    scene_files: Sequence[Path],
    config: ManimConfig,
    remote_cache: str,
) -> List[CheckItem]:
    items: List[CheckItem] = []
    cache = remote_cache.rstrip("/")
    if cache.startswith("~/"):
        cache = "$HOME/" + cache[2:]
    for scene_file in scene_files:
        scenes = parse_scene_file(Path(scene_file))
        if not scenes:
            raise ConfigError("%s: no class with a SCRIPT dict" % scene_file)
        for scene in scenes:
            label = scene.video_code or scene.class_name
            for index, (beat_key, text) in enumerate(scene.beats):
                prev_text = scene.beats[index - 1][1] if index > 0 else None
                next_text = scene.beats[index + 1][1] if index + 1 < len(scene.beats) else None
                digest = manim_identity_hash(text, prev_text, next_text, config)
                remote = "%s/%s/%s.mp3" % (cache, config.voice_id, digest)
                items.append(CheckItem(
                    id="%s:%s" % (label, beat_key),
                    intended=text,
                    remote_path=remote,
                    display_path=remote.replace("$HOME", "~"),
                ))
    return items


# ---------------------------------------------------------------------------
# The remote whisper batch (one ssh session per run)
# ---------------------------------------------------------------------------
def _shell_arg(path: str) -> str:
    if path.startswith("~/"):
        path = "$HOME/" + path[2:]
    if path.startswith("$HOME/"):
        return '"' + path.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`") + '"'
    return shlex.quote(path)


def build_remote_script(entries: Sequence[Tuple[int, str]], nonce: str) -> str:
    """A bash script that converts and transcribes every entry in one process."""
    begin = "@@LISTEN_BEGIN_%s:%%s@@" % nonce
    end = "@@LISTEN_END_%s:%%s@@" % nonce
    lines = [
        "#!/bin/bash",
        "set -u",
        'WHISPER=%s' % shlex.quote(WHISPER_BIN),
        'FFMPEG=%s' % shlex.quote(FFMPEG_BIN),
        'MODEL="%s"' % WHISPER_MODEL,
        'TMP=$(mktemp -d) || exit 4',
        'trap \'rm -rf "$TMP"\' EXIT',
        "",
        "run_one() {",
        '  idx="$1"',
        '  src="$2"',
        '  wav="$TMP/$idx.wav"',
        '  err="$TMP/$idx.err"',
        "  printf '\\n" + begin + "\\n' \"$idx\"",
        '  if ! "$FFMPEG" -nostdin -y -loglevel error -i "$src" -ar 16000 -ac 1 "$wav" 2>"$err"; then',
        "    printf '@@LISTEN_ERROR@@ ffmpeg: '",
        '    tr \'\\n\' \' \' < "$err" | head -c 500',
        "    printf '\\n'",
        "    printf '" + end + "\\n' \"$idx\"",
        "    return 0",
        "  fi",
        '  if ! text=$("$WHISPER" -m "$MODEL" -nt -np -f "$wav" 2>"$err"); then',
        "    printf '@@LISTEN_ERROR@@ whisper: '",
        '    tr \'\\n\' \' \' < "$err" | head -c 500',
        "    printf '\\n'",
        "    printf '" + end + "\\n' \"$idx\"",
        "    return 0",
        "  fi",
        "  printf '%s' \"$text\"",
        "  printf '\\n" + end + "\\n' \"$idx\"",
        "}",
        "",
    ]
    for index, source in entries:
        lines.append("run_one %d %s" % (index, _shell_arg(source)))
    lines.append("exit 0")
    return "\n".join(lines) + "\n"


def parse_batch_output(output: str, nonce: str, count: int) -> List[Tuple[Optional[str], Optional[str]]]:
    """Return (transcript, error) for each job index."""
    pattern = re.compile(
        r"@@LISTEN_BEGIN_%s:(\d+)@@(.*?)@@LISTEN_END_%s:\1@@"
        % (re.escape(nonce), re.escape(nonce)),
        re.S,
    )
    results: Dict[int, Tuple[Optional[str], Optional[str]]] = {}
    for match in pattern.finditer(output):
        index = int(match.group(1))
        body = match.group(2).strip()
        error_match = re.search(r"@@LISTEN_ERROR@@\s*(.*)", body, re.S)
        if error_match:
            message = " ".join(error_match.group(1).split())[:500]
            results[index] = (None, message or "remote transcription failed")
        else:
            results[index] = (body, None)
    missing = []
    for index in range(count):
        if index not in results:
            missing.append(index)
            results[index] = (None, "no transcript returned by the remote batch")
    return [results[index] for index in range(count)]


def transcribe_jobs(
    jobs: Sequence[Job],
    host: str = DEFAULT_HOST,
    timeout: float = SSH_TIMEOUT,
) -> List[Tuple[Optional[str], Optional[str]]]:
    """Send all clips to the Mini in one ssh session and return transcripts."""
    if not jobs:
        return []

    nonce = secrets.token_hex(4)
    entries: List[Tuple[int, str]] = []
    archive_names: Dict[int, str] = {}
    for job in jobs:
        if job.local_path is not None:
            suffix = job.local_path.suffix or ".audio"
            archive_names[job.index] = "clips/%d%s" % (job.index, suffix)
            entries.append((job.index, archive_names[job.index]))
        else:
            if not job.remote_path:
                raise ConfigError("job %s has neither a local nor a remote clip" % job.index)
            entries.append((job.index, job.remote_path))

    script = build_remote_script(entries, nonce)
    with tempfile.TemporaryDirectory(prefix="listen_check_") as temp_dir:
        tar_path = Path(temp_dir) / "batch.tar"
        with tarfile.open(tar_path, "w") as archive:
            data = script.encode("utf-8")
            info = tarfile.TarInfo("run.sh")
            info.size = len(data)
            info.mode = 0o755
            archive.addfile(info, io.BytesIO(data))
            for job in jobs:
                if job.local_path is None:
                    continue
                if not job.local_path.is_file():
                    raise ConfigError("local clip not found: %s" % job.local_path)
                archive.add(
                    str(job.local_path),
                    arcname=archive_names[job.index],
                )

        remote_command = (
            'd=$(mktemp -d) || exit 4; '
            'cd "$d" || exit 4; '
            'tar -xf - || { cd /; rm -rf "$d"; exit 4; }; '
            'bash ./run.sh; rc=$?; cd /; rm -rf "$d"; exit $rc'
        )
        command = [
            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
            host, remote_command,
        ]
        try:
            with tar_path.open("rb") as stdin:
                process = subprocess.run(
                    command, stdin=stdin, capture_output=True, timeout=timeout,
                )
        except subprocess.TimeoutExpired:
            raise RuntimeError("ssh/whisper timed out after %.0f s" % timeout)
        except OSError as err:
            raise RuntimeError("could not run ssh: %s" % err)

    if process.returncode != 0:
        stderr = process.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(
            "remote batch failed (ssh exit %d)%s"
            % (process.returncode, ": " + stderr[-1000:] if stderr else "")
        )
    return parse_batch_output(
        process.stdout.decode("utf-8", "replace"), nonce, len(jobs)
    )


# ---------------------------------------------------------------------------
# Running and reporting
# ---------------------------------------------------------------------------
def run_items(
    items: Sequence[CheckItem],
    threshold: float,
    host: str = DEFAULT_HOST,
    timeout: float = SSH_TIMEOUT,
) -> List[Dict]:
    job_keys: Dict[Tuple[str, str], int] = {}
    jobs: List[Job] = []
    for item in items:
        if item.pre_error:
            item.job_index = None
            continue
        if item.local_path is not None:
            key = ("local", str(item.local_path.resolve()))
        else:
            key = ("remote", str(item.remote_path))
        if key not in job_keys:
            index = len(jobs)
            job_keys[key] = index
            jobs.append(Job(
                index=index,
                local_path=item.local_path,
                remote_path=item.remote_path,
                display_path=item.display_path,
            ))
        item.job_index = job_keys[key]

    transcripts = transcribe_jobs(jobs, host=host, timeout=timeout)
    reports: List[Dict] = []
    for item in items:
        if item.pre_error:
            reports.append(analyze_clip(
                item.id, item.intended, None, threshold,
                clip_path=item.display_path, error=item.pre_error,
            ))
            continue
        transcript, error = transcripts[item.job_index]
        reports.append(analyze_clip(
            item.id, item.intended, transcript, threshold,
            clip_path=item.display_path, error=error,
        ))
    return reports


def _shorten(text: str, width: int) -> str:
    text = text or ""
    if len(text) <= width:
        return text
    return text[: max(0, width - 3)] + "..."


def print_table(reports: Sequence[Dict], threshold: float) -> None:
    headers = ("scene", "WER", "flags", "first difference")
    rows = []
    for report in reports:
        wer = "-" if report["wer"] is None else "%.3f" % report["wer"]
        flags = "; ".join(report["flags"]) or "-"
        rows.append((
            _shorten(report["id"], 46),
            wer,
            _shorten(flags, 44),
            _shorten(report["first_difference"] or "-", 52),
        ))
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i])
              for i in range(4)]
    line = "  ".join(headers[i].ljust(widths[i]) for i in range(4))
    print(line)
    print("  ".join("-" * widths[i] for i in range(4)))
    for row in rows:
        print("  ".join(row[i].ljust(widths[i]) for i in range(4)))
    flagged = sum(1 for report in reports if report["flagged"])
    print()
    print("%d clip%s, %d flagged at threshold %.2f"
          % (len(reports), "" if len(reports) == 1 else "s", flagged, threshold))


def write_report(path: Path, reports: Sequence[Dict], threshold: float,
                 command: str, host: str) -> None:
    path = Path(path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tool": "listen_check",
        "version": 1,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "command": command,
        "host": host,
        "threshold": threshold,
        "total": len(reports),
        "flagged": sum(1 for report in reports if report["flagged"]),
        "clips": list(reports),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _default_report_path(args) -> Path:
    if args.command == "tutorial":
        timeline = Path(args.timeline)
        return timeline.with_suffix(".listen.json")
    return Path("listen_check.report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="listen_check.py",
        description="Transcribe narration clips with whisper.cpp on the Mac Mini "
                    "and compare them with the intended script.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def common(sub):
        sub.add_argument("--report", type=Path,
                         help="JSON report path (default: next to the timeline, "
                              "or ./listen_check.report.json for manim)")
        sub.add_argument("--threshold", type=float, default=0.25,
                         help="flag a clip when its WER is above this (default 0.25)")
        sub.add_argument("--host", default=DEFAULT_HOST,
                         help="ssh host of the Mac Mini (default %(default)s)")
        sub.add_argument("--timeout", type=float, default=SSH_TIMEOUT,
                         help="ssh/whisper timeout in seconds (default %(default)s)")

    tutorial = subparsers.add_parser(
        "tutorial", help="check the clips in a <code>.timeline.json")
    tutorial.add_argument("timeline", type=Path)
    common(tutorial)

    manim = subparsers.add_parser(
        "manim", help="check the beats in one or more phy_*.py SCRIPT dicts")
    manim.add_argument("scenes", nargs="+", type=Path)
    manim.add_argument("--remote-cache", default=DEFAULT_REMOTE_CACHE,
                       help="clip cache on the Mini (default %(default)s)")
    common(manim)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "tutorial":
            items = load_tutorial_items(args.timeline)
            host = args.host
        else:
            manim_dir = find_manim_dir(args.scenes)
            config = load_manim_config(manim_dir)
            items = load_manim_items(args.scenes, config, args.remote_cache)
            host = args.host
        if not items:
            print("listen_check: no clips to check", file=sys.stderr)
            return 2
        reports = run_items(items, args.threshold, host=host, timeout=args.timeout)
    except (ConfigError, RuntimeError, ValueError, OSError, SyntaxError,
            json.JSONDecodeError) as err:
        print("listen_check: error: %s" % err, file=sys.stderr)
        return 2

    print_table(reports, args.threshold)
    if args.command == "manim" and reports and all(report["error"] for report in reports):
        print(
            "hint: no manim clips matched. Re-render after changing voice.env "
            "(ELEVEN_DIRECTION and ELEVEN_STABILITY are part of the cache key).",
            file=sys.stderr,
        )
    report_path = args.report or _default_report_path(args)
    try:
        write_report(report_path, reports, args.threshold,
                     command=" ".join([Path(sys.argv[0]).name] + list(argv if argv is not None else sys.argv[1:])),
                     host=host)
    except OSError as err:
        print("listen_check: error: cannot write report: %s" % err, file=sys.stderr)
        return 2
    print("report: %s" % report_path)
    return 1 if any(report["flagged"] for report in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
