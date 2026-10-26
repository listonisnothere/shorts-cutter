import pytest

from shorts_cutter.models import Clip, Segment, Transcript, Word
from shorts_cutter.selector import LEAD_IN, TAIL, fit_clips, format_transcript

# One word every 0.5 s for two minutes, each 0.4 s long.
WORDS = [Word(text=f"w{i}", start=i * 0.5, end=i * 0.5 + 0.4) for i in range(240)]


def clip(start: float, end: float, score: int = 5) -> Clip:
    return Clip(start=start, end=end, title="t", hook="h", reason="r", score=score)


def test_snaps_to_word_edges_with_padding():
    [c] = fit_clips([clip(10.0, 30.4)], WORDS, min_sec=15, max_sec=30)
    assert c.start == pytest.approx(10.0 - LEAD_IN)
    assert c.end == pytest.approx(30.4 + TAIL)


def test_long_clip_is_trimmed_to_max():
    [c] = fit_clips([clip(10.0, 50.0)], WORDS, min_sec=15, max_sec=30)
    assert c.duration <= 30
    assert c.duration > 29


def test_short_clip_is_dropped():
    assert fit_clips([clip(10.0, 20.0)], WORDS, min_sec=15, max_sec=30) == []


def test_overlap_keeps_higher_score():
    kept = fit_clips([clip(10, 30, score=4), clip(20, 40, score=9)], WORDS, min_sec=15, max_sec=30)
    assert [c.score for c in kept] == [9]


def test_clip_past_the_end_is_dropped():
    assert fit_clips([clip(500, 520)], WORDS, min_sec=15, max_sec=30) == []


def test_format_transcript():
    t = Transcript(words=[], segments=[Segment(text="Привет", start=1.234, end=2.0)])
    assert format_transcript(t) == "[1.2-2.0] Привет"
