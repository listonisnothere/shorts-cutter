"""Configuration from environment variables (prefix ``SHORTS_``) and ``.env``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Transcriber = Literal["openai", "elevenlabs"]

# shorts-cutter/, so the .env files are found whatever folder the command runs from.
PROJECT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SHORTS_",
        # content-factory/.env (shared by the ecosystem) and shorts-cutter/.env; later files win.
        env_file=(PROJECT_DIR.parent / ".env", PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SHORTS_OPENAI_API_KEY wins wherever it is set; the factory-wide OPENAI_API_KEY is the fallback.
    # Two explicitly aliased fields, because a field named OPENAI_API_KEY would collide with the fallback.
    MODULE_OPENAI_API_KEY: str = Field("", validation_alias="SHORTS_OPENAI_API_KEY")
    SHARED_OPENAI_API_KEY: str = Field("", validation_alias="OPENAI_API_KEY")
    ELEVENLABS_API_KEY: str = ""

    # openai = whisper-1, the only OpenAI model with word timestamps; OpenAI shuts it down 2027-02-26.
    TRANSCRIBER: Transcriber = "openai"
    ELEVENLABS_MODEL: str = "scribe_v2"
    SELECT_MODEL: str = "gpt-6.1-sol"

    FFMPEG_BIN: str = ""
    SUBTITLE_FONT: str = "Arial"
    SUBTITLE_SIZE: int = 84

    @property
    def openai_api_key(self) -> str | None:
        return self.MODULE_OPENAI_API_KEY or self.SHARED_OPENAI_API_KEY or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
