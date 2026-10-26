"""Thin ffmpeg wrappers: audio extraction for speech-to-text and the final 9:16 render."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Literal

from shorts_cutter.config import get_settings

Reframe = Literal["crop", "blur"]

# 9:16 at 1080x1920. "crop" keeps the centre of the frame; "blur" fits the whole frame over a blurred
# copy of itself, which suits slides and wide shots where a centre crop loses content.
REFRAME_FILTERS: dict[Reframe, str] = {
    "crop": "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=1080:1920,setsar=1",
    "blur": (
        "split[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=40[bg];"
        "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
    ),
}


def ffmpeg_bin() -> str:
    """``SHORTS_FFMPEG_BIN``, else ``ffmpeg`` on PATH, else the binary bundled with imageio-ffmpeg."""
    if configured := get_settings().FFMPEG_BIN:
        return configured
    if found := shutil.which("ffmpeg"):
        return found
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(args: list[str], cwd: Path | None = None) -> None:
    proc = subprocess.run(
        [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {proc.stderr.strip()}")


def extract_audio(video: Path, out: Path) -> Path:
    """Mono 16 kHz 32 kbps mp3: plenty for speech, ~14 MB per hour."""
    run_ffmpeg(
        ["-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "32k", str(out)]
    )
    return out


def split_audio(audio: Path, max_bytes: int, chunk_sec: int = 1200) -> list[Path]:
    """Split into ``chunk_sec`` pieces if the file is over ``max_bytes``; a word on a boundary may be cut."""
    if audio.stat().st_size <= max_bytes:
        return [audio]
    for old in audio.parent.glob(f"{audio.stem}_*{audio.suffix}"):
        old.unlink()
    pattern = audio.with_name(f"{audio.stem}_%03d{audio.suffix}")
    run_ffmpeg(
        ["-i", str(audio), "-f", "segment", "-segment_time", str(chunk_sec), "-c", "copy", str(pattern)]
    )
    return sorted(audio.parent.glob(f"{audio.stem}_[0-9][0-9][0-9]{audio.suffix}"))


def render_clip(video: Path, start: float, end: float, subtitles: Path, out: Path, reframe: Reframe) -> Path:
    """Cut [start, end], reframe to 9:16 and burn in ``subtitles`` (ASS, times relative to ``start``)."""
    # The ass filter takes a filtergraph-escaped path; running next to the file sidesteps escaping entirely.
    run_ffmpeg(
        [
            "-ss", f"{start:.3f}",
            "-i", str(video.resolve()),
            "-t", f"{end - start:.3f}",
            "-vf", f"{REFRAME_FILTERS[reframe]},ass={subtitles.name}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart",
            str(out.resolve()),
        ],
        cwd=subtitles.parent,
    )  # fmt: skip
    return out
