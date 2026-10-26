"""Captions in the usual shorts style: 1–3 words at a time, large, centred in the lower third.

ASS is burned into the video; SRT is written alongside for platforms and editors that take captions as a file.
"""

from __future__ import annotations

from typing import NamedTuple

from shorts_cutter.models import Word

MAX_WORDS = 3
MAX_CHARS = 18  # keeps a caption on one line at the default size on a 1080 px wide frame
MAX_GAP = 0.6  # a pause this long (seconds) starts a new caption and leaves the screen empty
SENTENCE_END = (".", "!", "?", "…")


class Caption(NamedTuple):
    start: float
    end: float
    text: str


def captions_for(words: list[Word], start: float, end: float) -> list[Caption]:
    """Group the words inside [start, end] into captions with times relative to ``start``."""
    groups: list[list[Word]] = []
    for word in (w for w in words if w.start >= start and w.end <= end):
        last = groups[-1] if groups else None
        if (
            last is None
            or len(last) >= MAX_WORDS
            or len(" ".join(w.text for w in last)) + 1 + len(word.text) > MAX_CHARS
            or word.start - last[-1].end > MAX_GAP
            or last[-1].text.endswith(SENTENCE_END)
        ):
            groups.append([word])
        else:
            last.append(word)

    captions: list[Caption] = []
    for n, group in enumerate(groups):
        cap_end = group[-1].end
        # Hold the caption until the next one appears across short gaps, so the text does not flicker.
        if n + 1 < len(groups) and groups[n + 1][0].start - cap_end <= MAX_GAP:
            cap_end = groups[n + 1][0].start
        captions.append(
            Caption(group[0].start - start, min(cap_end, end) - start, " ".join(w.text for w in group))
        )
    return captions


def to_ass(captions: list[Caption], font: str, size: int) -> str:
    # Colours are &HAABBGGRR: white text, black outline. Alignment 2 = bottom centre, MarginV lifts it
    # into the lower third, clear of the platform's own buttons and caption.
    header = f"""\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,2,80,80,560,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""  # noqa: E501 — ASS section lines cannot be wrapped
    events = [
        f"Dialogue: 0,{_ass_time(c.start)},{_ass_time(c.end)},Default,,0,0,0,,{_ass_text(c.text)}"
        for c in captions
    ]
    return header + "\n".join(events) + "\n"


def to_srt(captions: list[Caption]) -> str:
    blocks = [
        f"{n}\n{_srt_time(c.start)} --> {_srt_time(c.end)}\n{c.text}\n" for n, c in enumerate(captions, 1)
    ]
    return "\n".join(blocks)


def _ass_text(text: str) -> str:
    # Braces start override tags and backslashes start escapes; ASS has no way to quote either.
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def _ass_time(sec: float) -> str:
    cs = round(sec * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _srt_time(sec: float) -> str:
    ms = round(sec * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
