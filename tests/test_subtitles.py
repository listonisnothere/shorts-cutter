from shorts_cutter.models import Word
from shorts_cutter.subtitles import Caption, _ass_time, _srt_time, captions_for, to_ass, to_srt


def words(*items: tuple[str, float, float]) -> list[Word]:
    return [Word(text=t, start=s, end=e) for t, s, e in items]


def test_groups_at_most_three_words_relative_to_clip_start():
    ws = words(*((f"w{i}", 10 + i * 0.3, 10 + i * 0.3 + 0.25) for i in range(7)))
    caps = captions_for(ws, start=10.0, end=13.0)
    assert [c.text for c in caps] == ["w0 w1 w2", "w3 w4 w5", "w6"]
    assert caps[0].start == 0.0


def test_long_pause_and_sentence_end_break_captions():
    ws = words(("Привет.", 0.0, 0.4), ("Как", 0.5, 0.7), ("дела", 0.8, 1.0), ("потом", 2.0, 2.3))
    assert [c.text for c in captions_for(ws, 0.0, 3.0)] == ["Привет.", "Как дела", "потом"]


def test_caption_holds_across_short_gap_but_not_long_one():
    ws = words(("a", 0.0, 0.2), ("b.", 0.3, 0.5), ("c", 0.7, 0.9), ("d", 2.0, 2.2))
    caps = captions_for(ws, 0.0, 3.0)
    assert caps[0].end == 0.7  # held until "c" appears
    assert caps[1].end == 0.9  # 1.1 s pause before "d": screen goes empty


def test_long_words_split_by_character_budget():
    ws = words(("сверхъестественный", 0, 1), ("невероятно", 1, 2))
    assert len(captions_for(ws, 0, 2)) == 2


def test_words_outside_clip_are_skipped():
    ws = words(("before", 0, 1), ("inside", 5, 6), ("after", 9, 10))
    assert [c.text for c in captions_for(ws, 4.9, 6.3)] == ["inside"]


def test_time_formats():
    assert _ass_time(3725.456) == "1:02:05.46"
    assert _srt_time(3725.456) == "01:02:05,456"


def test_ass_strips_override_characters():
    ass = to_ass([Caption(0, 1, r"{\b1}hi")], "Arial", 84)
    assert "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,(b1)hi" in ass
    assert "PlayResY: 1920" in ass


def test_srt_numbering():
    assert to_srt([Caption(0, 1, "a"), Caption(1, 2, "b")]) == (
        "1\n00:00:00,000 --> 00:00:01,000\na\n\n2\n00:00:01,000 --> 00:00:02,000\nb\n"
    )
