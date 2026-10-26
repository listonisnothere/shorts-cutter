"""Speech-to-text with word timestamps, which subtitles and frame-accurate cuts both depend on.

OpenAI: only ``whisper-1`` returns word timestamps (the recommended ``gpt-transcribe`` returns plain text),
and OpenAI shuts ``whisper-1`` down on 2027-02-26. ElevenLabs Scribe returns word timestamps, handles
Russian and Kazakh, and accepts files up to 5 GB, so it needs no chunking.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from openai import OpenAI, omit

from shorts_cutter import media
from shorts_cutter.config import Transcriber, get_settings
from shorts_cutter.models import Segment, Transcript, Word

OPENAI_MAX_UPLOAD_BYTES = 24 * 1024 * 1024  # API limit is 25 MB
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/speech-to-text"

SENTENCE_END = (".", "!", "?", "…")
SEGMENT_PAUSE = 1.0  # seconds of silence that end a segment even without punctuation
SEGMENT_MAX = 20.0


def transcribe(audio: Path, language: str | None = None, provider: Transcriber | None = None) -> Transcript:
    provider = provider or get_settings().TRANSCRIBER
    if provider == "elevenlabs":
        return _transcribe_elevenlabs(audio, language)
    return _transcribe_openai(audio, language)


def _transcribe_openai(audio: Path, language: str | None) -> Transcript:
    client = OpenAI(api_key=get_settings().openai_api_key)
    words: list[Word] = []
    segments: list[Segment] = []
    detected: str | None = None
    offset = 0.0
    for chunk in media.split_audio(audio, OPENAI_MAX_UPLOAD_BYTES):
        with chunk.open("rb") as f:
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"],
                language=language or omit,
            )
        words += [Word(text=w.word, start=w.start + offset, end=w.end + offset) for w in resp.words or []]
        segments += [
            Segment(text=s.text.strip(), start=s.start + offset, end=s.end + offset)
            for s in resp.segments or []
        ]
        detected = detected or resp.language
        offset += resp.duration
    return Transcript(language=detected, words=words, segments=segments)


def _transcribe_elevenlabs(audio: Path, language: str | None) -> Transcript:
    settings = get_settings()
    form = {
        "model_id": settings.ELEVENLABS_MODEL,
        "timestamps_granularity": "word",
        "tag_audio_events": "false",
    }
    if language:
        form["language_code"] = language
    with audio.open("rb") as f:
        resp = httpx.post(
            ELEVENLABS_URL,
            headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
            data=form,
            files={"file": (audio.name, f, "audio/mpeg")},
            timeout=httpx.Timeout(30.0, read=1800.0),  # an hour of audio takes minutes
        )
    resp.raise_for_status()
    return parse_elevenlabs(resp.json())


def parse_elevenlabs(body: dict) -> Transcript:
    words = [
        Word(text=w["text"], start=w["start"], end=w["end"])
        for w in body["words"]
        if w["type"] == "word" and w.get("start") is not None
    ]
    return Transcript(language=body.get("language_code"), words=words, segments=group_segments(words))


def group_segments(words: list[Word]) -> list[Segment]:
    """Sentence-like segments from punctuated words, for providers that return words only."""
    segments: list[Segment] = []
    current: list[Word] = []
    for i, word in enumerate(words):
        current.append(word)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if (
            nxt is None
            or word.text.endswith(SENTENCE_END)
            or nxt.start - word.end >= SEGMENT_PAUSE
            or nxt.end - current[0].start > SEGMENT_MAX
        ):
            segments.append(
                Segment(text=" ".join(w.text for w in current), start=current[0].start, end=current[-1].end)
            )
            current = []
    return segments
