"""Data shapes passed between pipeline stages. Times are seconds from the start of the source video."""

from __future__ import annotations

from pydantic import BaseModel


class Word(BaseModel):
    text: str
    start: float
    end: float


class Segment(BaseModel):
    """A sentence-like span of speech: the unit the LLM sees when it picks clips."""

    text: str
    start: float
    end: float


class Transcript(BaseModel):
    language: str | None = None
    words: list[Word]
    segments: list[Segment]


class Clip(BaseModel):
    """Also the structured-output schema the LLM fills in, so field order and names are part of the prompt."""

    start: float
    end: float
    title: str
    hook: str
    reason: str
    score: int

    @property
    def duration(self) -> float:
        return self.end - self.start
