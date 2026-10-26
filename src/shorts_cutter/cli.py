"""``uv run shorts-cutter VIDEO``: cut a long video into vertical shorts with subtitles."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from shorts_cutter import pipeline
from shorts_cutter.config import Transcriber
from shorts_cutter.media import Reframe

app = typer.Typer(add_completion=False)


@app.command()
def main(
    video: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="Source video file.")],
    out: Annotated[Path, typer.Option(help="Output root; files go to <out>/<video name>/.")] = Path("out"),
    count: Annotated[int, typer.Option(help="Maximum number of shorts to make.")] = 8,
    min_sec: Annotated[float, typer.Option("--min", help="Minimum short length, seconds.")] = 15,
    max_sec: Annotated[float, typer.Option("--max", help="Maximum short length, seconds.")] = 30,
    language: Annotated[str | None, typer.Option(help="Speech language as ISO-639-1 (ru, kk, en).")] = None,
    transcriber: Annotated[Transcriber | None, typer.Option(help="Overrides SHORTS_TRANSCRIBER.")] = None,
    reframe: Annotated[Reframe, typer.Option(help="crop: centre crop; blur: full frame on blur.")] = "crop",
    retranscribe: Annotated[bool, typer.Option(help="Ignore the cached transcript.json.")] = False,
    reselect: Annotated[
        bool,
        typer.Option(
            help="Pick new clips instead of reusing clips.json (after changing --count/--min/--max)."
        ),
    ] = False,
    dry_run: Annotated[
        bool, typer.Option(help="Write clips.json without rendering; the next run renders those clips.")
    ] = False,
) -> None:
    clips = pipeline.run(
        video,
        out,
        count=count,
        min_sec=min_sec,
        max_sec=max_sec,
        language=language,
        transcriber=transcriber,
        reframe=reframe,
        retranscribe=retranscribe,
        reselect=reselect,
        render=not dry_run,
    )
    typer.echo(f"{len(clips)} shorts → {out / video.stem}")
    for n, clip in enumerate(clips, 1):
        typer.echo(
            f"  clip_{n:02d}  {_mmss(clip.start)}–{_mmss(clip.end)}  {clip.duration:4.1f}s"
            f"  {clip.score:>2}/10  {clip.title}"
        )


def _mmss(sec: float) -> str:
    return f"{int(sec // 60):02d}:{sec % 60:04.1f}"
