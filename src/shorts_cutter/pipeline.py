"""video → transcript → clip selection → rendered shorts, with all artefacts in ``<out>/<video stem>/``.

Both paid steps are cached: the transcript in ``transcript.json`` and the picked clips in ``clips.json``.
A dry run picks clips for review; the next run renders exactly those, including any hand edits to the file.
"""

from __future__ import annotations

import json
from pathlib import Path

from shorts_cutter import media
from shorts_cutter.config import Transcriber, get_settings
from shorts_cutter.media import Reframe
from shorts_cutter.models import Clip, Transcript
from shorts_cutter.selector import select_clips
from shorts_cutter.subtitles import captions_for, to_ass, to_srt
from shorts_cutter.transcribe import transcribe


def run(
    video: Path,
    out_root: Path,
    *,
    count: int = 8,
    min_sec: float = 15,
    max_sec: float = 30,
    language: str | None = None,
    transcriber: Transcriber | None = None,
    reframe: Reframe = "crop",
    retranscribe: bool = False,
    reselect: bool = False,
    render: bool = True,
) -> list[Clip]:
    work = out_root / video.stem
    work.mkdir(parents=True, exist_ok=True)

    transcript_path = work / "transcript.json"
    if transcript_path.exists() and not retranscribe:
        transcript = Transcript.model_validate_json(transcript_path.read_text())
    else:
        audio = media.extract_audio(video, work / "audio.mp3")
        transcript = transcribe(audio, language=language, provider=transcriber)
        transcript_path.write_text(transcript.model_dump_json(indent=2))
    if not transcript.words:
        raise RuntimeError(f"no speech found in {video}")

    clips_path = work / "clips.json"
    if clips_path.exists() and not (reselect or retranscribe):
        clips = [Clip.model_validate(item) for item in json.loads(clips_path.read_text())]
    else:
        clips = select_clips(transcript, count=count, min_sec=min_sec, max_sec=max_sec)
    # Rewritten on reuse too, so "file" matches the numbering after clips were deleted by hand.
    manifest = [{"file": f"clip_{n:02d}.mp4", **clip.model_dump()} for n, clip in enumerate(clips, 1)]
    clips_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    if render:
        settings = get_settings()
        for old in work.glob("clip_*"):  # a previous render may have had more clips
            old.unlink()
        for n, clip in enumerate(clips, 1):
            name = f"clip_{n:02d}"
            captions = captions_for(transcript.words, clip.start, clip.end)
            ass = work / f"{name}.ass"
            ass.write_text(to_ass(captions, settings.SUBTITLE_FONT, settings.SUBTITLE_SIZE))
            (work / f"{name}.srt").write_text(to_srt(captions))
            media.render_clip(video, clip.start, clip.end, ass, work / f"{name}.mp4", reframe)
    return clips
