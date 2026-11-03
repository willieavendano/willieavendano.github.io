"""
srt.py — captions from the same scene timings that drive the track
==================================================================

One narration beat becomes one or more subtitles. A beat's spoken text is
wrapped to at most `max_lines` lines of `max_words_per_line` words, and the
beat's time span is split across its subtitles in proportion to word count,
with a 60 ms gap between them. Timestamps are `HH:MM:SS,mmm` and cues are
numbered from 1, separated by blank lines (script-format.md, step 4).

Breaks prefer sentence and clause punctuation, so a line tends to end where
the narrator would pause rather than mid-phrase.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple

GAP_SECONDS = 0.06
_DEFAULT_LINE_WORDS = 7
_DEFAULT_LINES = 2

_SENTENCE_END = ".!?…"
_CLAUSE_END = ",;:—–-"


def format_timestamp(seconds: float) -> str:
    """Seconds -> `HH:MM:SS,mmm`, clamped at zero."""
    millis = int(round(max(0.0, float(seconds)) * 1000))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return "{:02d}:{:02d}:{:02d},{:03d}".format(hours, minutes, secs, millis)


def _ends_clause(word: str) -> bool:
    token = word.rstrip("\"'”’)]}")
    return bool(token) and token[-1] in (_SENTENCE_END + _CLAUSE_END)


def _wrap(words: Sequence[str], max_words_per_line: int) -> str:
    """Join words into the fewest balanced lines that respect the word cap."""
    if not words:
        return ""
    chunk = list(words)
    if len(chunk) <= max_words_per_line:
        return " ".join(chunk)
    line_count = -(-len(chunk) // max_words_per_line)  # ceil
    size, extra = divmod(len(chunk), line_count)
    lines = []
    pos = 0
    for line_index in range(line_count):
        take = size + (1 if line_index < extra else 0)
        lines.append(" ".join(chunk[pos:pos + take]))
        pos += take
    return "\n".join(lines)


def split_text(text: str, max_words_per_line: int = _DEFAULT_LINE_WORDS,
               max_lines: int = _DEFAULT_LINES) -> List[str]:
    """Split one cue's text into subtitle texts (each <= max_lines wrapped lines).

    Splits on the punctuation nearest the allowed word budget, so a subtitle
    ends at a comma or full stop when one is available. Text with no
    punctuation at all is cut at the word budget.
    """
    words = (text or "").split()
    if not words:
        return []
    per_line = max(1, int(max_words_per_line))
    line_cap = max(1, int(max_lines))
    capacity = per_line * line_cap

    parts: List[List[str]] = []
    index = 0
    while index < len(words):
        remaining = len(words) - index
        if remaining <= capacity:
            parts.append(words[index:])
            break
        far = index + capacity
        near = index + max(1, capacity // 2)
        cut = far
        for candidate in range(far, near - 1, -1):
            if _ends_clause(words[candidate - 1]):
                cut = candidate
                break
        parts.append(words[index:cut])
        index = cut

    return [_wrap(part, per_line) for part in parts]


def _cue_subtitles(start: float, end: float, subtitles: List[str]) -> List[Tuple[float, float, str]]:
    """Distribute [start, end] across subtitles in proportion to word count."""
    span = max(0.0, end - start)
    count = len(subtitles)
    gap = GAP_SECONDS if count > 1 else 0.0
    available = span - gap * (count - 1)
    if available <= 0.0:  # too short for the gaps: drop them, keep order
        gap = 0.0
        available = span

    weights = [max(1, len(text.split())) for text in subtitles]
    total_weight = float(sum(weights))
    cursor = start
    cues = []
    for index, (text, weight) in enumerate(zip(subtitles, weights)):
        length = available * (weight / total_weight) if total_weight else available
        cue_end = cursor + length
        if index == count - 1:
            cue_end = end  # absorb float drift into the final cue
        cues.append((cursor, cue_end, text))
        cursor = cue_end + gap
    return cues


def write_srt(cues: Sequence[Tuple[float, float, str]], path: Path,
              max_words_per_line: int = _DEFAULT_LINE_WORDS,
              max_lines: int = _DEFAULT_LINES) -> Path:
    """Write cues [(start_s, end_s, text)] as numbered, blank-line-separated SRT."""
    path = Path(path)
    blocks: List[str] = []
    number = 0
    for start, end, text in cues:
        start = max(0.0, float(start))
        end = max(start, float(end))
        subtitles = split_text(text, max_words_per_line, max_lines)
        if not subtitles:
            continue
        for cue_start, cue_end, cue_text in _cue_subtitles(start, end, subtitles):
            number += 1
            blocks.append("{}\n{} --> {}\n{}\n".format(
                number,
                format_timestamp(cue_start),
                format_timestamp(cue_end),
                cue_text,
            ))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path