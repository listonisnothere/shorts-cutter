from shorts_cutter.models import Word
from shorts_cutter.transcribe import group_segments, parse_elevenlabs


def test_parse_elevenlabs_keeps_timed_words_only():
    body = {
        "language_code": "rus",
        "words": [
            {"text": "Привет.", "type": "word", "start": 0.0, "end": 0.5, "logprob": 0},
            {"text": " ", "type": "spacing", "start": 0.5, "end": 0.6, "logprob": 0},
            {"text": "(смех)", "type": "audio_event", "start": 0.6, "end": 1.0, "logprob": 0},
            {"text": "Это", "type": "word", "start": 1.0, "end": 1.2, "logprob": 0},
            {"text": "мы", "type": "word", "start": None, "end": None, "logprob": 0},
        ],
    }
    t = parse_elevenlabs(body)
    assert [w.text for w in t.words] == ["Привет.", "Это"]
    assert t.language == "rus"
    assert [s.text for s in t.segments] == ["Привет.", "Это"]


def test_segments_split_on_punctuation_pause_and_length():
    ws = [
        Word(text="Раз", start=0, end=0.3),
        Word(text="два.", start=0.4, end=0.7),
        Word(text="три", start=0.8, end=1.0),
        Word(text="четыре", start=2.5, end=2.9),  # 1.5 s pause
    ]
    assert [s.text for s in group_segments(ws)] == ["Раз два.", "три", "четыре"]

    long_run = [Word(text="w", start=i, end=i + 0.9) for i in range(45)]
    assert all(s.end - s.start <= 20 for s in group_segments(long_run))
