"""Pick standalone 15–30 s moments from the transcript with an LLM, then fit them to word boundaries.

The model only reads the transcript, so it judges what is said, not what is shown. A moment that works
visually but has no speech (a reaction, a demo) is invisible to it.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right

from openai import OpenAI
from pydantic import BaseModel

from shorts_cutter.config import get_settings
from shorts_cutter.models import Clip, Transcript, Word

SNAP_TOLERANCE = 0.3  # the model sees times rounded to 0.1 s
LEAD_IN = 0.1  # seconds kept before the first word
TAIL = 0.3  # and after the last one, so the cut does not clip the final syllable

INSTRUCTIONS = """\
You cut long videos into vertical shorts for TikTok, Instagram Reels and YouTube Shorts.
The input is the video's transcript. Each line is "[start-end] text", times in seconds.

Pick up to {count} clips. Every clip must:
- last {min_sec:g}-{max_sec:g} seconds (end - start);
- start at the start time of a line and end at the end time of a line;
- make sense to a viewer who has not seen the rest of the video: one complete idea, story, answer \
or punchline;
- open with a hook in the first 3 seconds (a strong claim, a question, a surprise, an emotion), never \
mid-sentence and never with filler words;
- end on a finished thought.
Clips must not overlap. Fewer strong clips beat many weak ones.

title: a catchy title for the short, in the transcript's language, at most 60 characters.
hook: the opening line, as spoken.
reason: one sentence on why this works as a standalone short.
score: 1-10, how likely the clip is to hold a viewer's attention."""


class ClipPlan(BaseModel):
    clips: list[Clip]


def select_clips(transcript: Transcript, *, count: int, min_sec: float, max_sec: float) -> list[Clip]:
    proposed = _ask_model(transcript, count=count, min_sec=min_sec, max_sec=max_sec)
    return fit_clips(proposed, transcript.words, min_sec=min_sec, max_sec=max_sec)


def _ask_model(transcript: Transcript, *, count: int, min_sec: float, max_sec: float) -> list[Clip]:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.parse(
        model=settings.SELECT_MODEL,
        instructions=INSTRUCTIONS.format(count=count, min_sec=min_sec, max_sec=max_sec),
        input=format_transcript(transcript),
        text_format=ClipPlan,
    )
    if response.output_parsed is None:
        raise RuntimeError(f"model returned no clip plan: {response.output_text!r}")
    return response.output_parsed.clips


def format_transcript(transcript: Transcript) -> str:
    return "\n".join(f"[{s.start:.1f}-{s.end:.1f}] {s.text}" for s in transcript.segments)


def fit_clips(clips: list[Clip], words: list[Word], *, min_sec: float, max_sec: float) -> list[Clip]:
    """Snap proposed bounds to word edges, enforce the duration range and drop overlaps. Best score first.

    A clip that runs long is trimmed at the last word that fits; one that ends up short is dropped.
    """
    starts = [w.start for w in words]
    ends = [w.end for w in words]
    fitted: list[Clip] = []
    for clip in sorted(clips, key=lambda c: c.score, reverse=True):
        i = bisect_left(starts, clip.start - SNAP_TOLERANCE)
        if i >= len(words):
            continue
        start = max(0.0, words[i].start - LEAD_IN)
        limit = min(clip.end + SNAP_TOLERANCE, start + max_sec - TAIL)
        j = bisect_right(ends, limit) - 1
        if j < i:
            continue
        end = words[j].end + TAIL
        if end - start < min_sec or any(start < c.end and c.start < end for c in fitted):
            continue
        fitted.append(clip.model_copy(update={"start": round(start, 3), "end": round(end, 3)}))
    return fitted
