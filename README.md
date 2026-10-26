# shorts-cutter

Turns a long video into vertical shorts: 15–30 seconds, 1080×1920, with burned-in subtitles. AI picks
moments that make sense on their own and open with a hook; ffmpeg cuts them, makes them vertical and adds
captions. Part of Content Factory.

```
video.mp4 → transcribe (timing of every word) → AI picks moments → cut, 9:16, subtitles → clip_01.mp4 …
```

Which APIs it uses, why, and what they cost: [docs/RESEARCH.md](docs/RESEARCH.md) (in Russian).

## Setup

Once per machine. You need [uv](https://docs.astral.sh/uv/); it installs Python 3.12 and every dependency,
ffmpeg included.

```bash
cd content-factory/shorts-cutter
uv sync                  # install dependencies into .venv
cp .env.example .env     # then put your OpenAI key in SHORTS_OPENAI_API_KEY
```

An OpenAI key is the only one you need. If `OPENAI_API_KEY` is already set in your shell or in the shared
`content-factory/.env`, you can leave `SHORTS_OPENAI_API_KEY` empty.

## Quick start

```bash
# 1. Pick the moments. This is the paid step: transcription plus one AI call. Nothing is cut yet.
uv run shorts-cutter video.mp4 --language ru --dry-run

# 2. Open out/video/clips.json. Delete clips you don't want; adjust start/end if needed.

# 3. Cut the clips you kept. Free: runs on your machine, no API calls.
uv run shorts-cutter video.mp4 --language ru
```

The shorts land in `out/video/`: `clip_01.mp4`, `clip_02.mp4`, … with the best first.

Run commands from the `shorts-cutter` folder. Video paths are relative to the folder you are in:
`demo/video.mp4`, not `/demo/video.mp4`.

## Command reference

```
uv run shorts-cutter VIDEO [OPTIONS]
```

| Option | Default | What it does |
|---|---|---|
| `VIDEO` | required | Source video. Any format ffmpeg reads: mp4, mov, mkv, webm… |
| `--language CODE` | auto-detect | Language that is **spoken** in the video, as a two-letter code: `ru`, `kk`, `en`, `hi`… Setting it avoids wrong guesses. A different language than the one spoken gives translated subtitles. |
| `--dry-run` | off | Pick clips and write `clips.json`, but don't cut. |
| `--count N` | `8` | Most shorts to make. You may get fewer; see [Troubleshooting](#troubleshooting). |
| `--min SEC` | `15` | Shortest allowed short, in seconds. |
| `--max SEC` | `30` | Longest allowed short, in seconds. |
| `--reframe crop\|blur` | `crop` | How a landscape video becomes vertical. `crop` keeps the centre of the frame. `blur` keeps the whole frame on a blurred background. |
| `--reselect` | off | Ask the AI for new picks instead of reusing `clips.json`. |
| `--retranscribe` | off | Transcribe again instead of reusing `transcript.json`. Also picks new clips. |
| `--transcriber openai\|elevenlabs` | `openai`, or `SHORTS_TRANSCRIBER` | Speech-to-text service for this run. |
| `--out DIR` | `out` | Where results go. Each video gets its own `DIR/<video name>/` folder. |
| `--help` | | List all options. |

Saved results are reused, so some options only take effect together with a flag that redoes their step:

- `--count`, `--min`, `--max`: only used when clips are picked. Add `--reselect`.
- `--language`, `--transcriber`: only used when transcribing. Add `--retranscribe`.

## What each run does, and what it costs

Each run reuses what it already has for that video, so the paid steps run once:

| Step | Runs when | Cost for 1 hour of video |
|---|---|---|
| Transcription | First run, or `--retranscribe` | $0.36 with OpenAI, $0.22 with ElevenLabs |
| Picking clips | First run, `--reselect` or `--retranscribe` | About $0.05–0.10 |
| Cutting | Every run without `--dry-run` | Free. 7 clips took about a minute on a MacBook Air |

## Recipes

**Drop or adjust a clip.** Edit `out/<video name>/clips.json`, then run without `--dry-run`:

```json
{
  "file": "clip_01.mp4",
  "start": 208.62,
  "end": 238.22,
  "title": "Stop Giving Every Chapter Equal Time",
  "hook": "Sneha's biggest mistake was that she started reading from page 1.",
  "reason": "A relatable study mistake turns into a concrete lesson about prioritizing chapters by exam weight.",
  "score": 9
}
```

- Delete an entry to skip that clip. The rest are numbered in file order, and `file` is updated to match.
- `start` and `end` are seconds from the beginning of the source video. Edited times are used exactly as
  written: they aren't snapped to word boundaries or checked against `--min`/`--max`.
- Subtitles are rebuilt from the transcript for whatever times you set.

**Get a different set of clips.**

```bash
uv run shorts-cutter video.mp4 --reselect --dry-run
```

**Fewer, longer or shorter clips.**

```bash
uv run shorts-cutter video.mp4 --count 5 --min 20 --max 30 --reselect
```

**Keep the whole frame** for slides, on-screen titles or wide shots, where `crop` cuts things off.

```bash
uv run shorts-cutter video.mp4 --reframe blur
```

This re-cuts the same picks and replaces the clip files in that folder.

**Russian or Kazakh video.** Titles and hooks come out in the video's language.

```bash
uv run shorts-cutter talk.mp4 --language ru
uv run shorts-cutter talk.mp4 --language kk
```

**Transcribe with ElevenLabs instead of OpenAI.** Put your key in `SHORTS_ELEVENLABS_API_KEY`, then:

```bash
uv run shorts-cutter video.mp4 --transcriber elevenlabs --retranscribe
```

`--retranscribe` is only needed if the video already has a transcript from OpenAI. To make ElevenLabs the
default, set `SHORTS_TRANSCRIBER=elevenlabs` in `.env`. OpenAI shuts down `whisper-1`, the transcription
model used here, on 26 February 2027, so switch before then.

**Save results somewhere else.**

```bash
uv run shorts-cutter video.mp4 --out ~/Desktop/shorts
```

**Process a folder of videos.**

```bash
for f in videos/*.mp4; do uv run shorts-cutter "$f" --language ru; done
```

Results are grouped by file name, so two videos with the same name in different folders share one output
folder and overwrite each other.

**Run from another folder.** Settings still come from `shorts-cutter/.env`; results go to `out/` in the
folder you run from.

```bash
uv run --project path/to/shorts-cutter shorts-cutter video.mp4
```

**Start a video over from scratch.**

```bash
rm -rf out/video
```

## Output files

Everything for a video is in `out/<video name>/`:

| File | What it is |
|---|---|
| `clip_01.mp4` … | The shorts: 1080×1920, H.264 + AAC, subtitles burned in, best first. |
| `clip_01.srt` … | The same subtitles as a separate file, for platforms or editors that take captions separately. |
| `clip_01.ass` … | Styled subtitles used for the burn-in. |
| `clips.json` | The picked clips: file, start, end, title, hook, reason, score. Edit it to change what gets cut. |
| `transcript.json` | Every word with its timing. Reused on later runs. |
| `audio.mp3` | Audio extracted for transcription. Safe to delete. |

Each cut deletes the folder's previous `clip_*` files first.

## Settings

Settings are read from `shorts-cutter/.env` and the shared `content-factory/.env`; `shorts-cutter/.env`
wins. Variables set in your shell override both. All are optional except an OpenAI key.

| Variable | Default | Meaning |
|---|---|---|
| `SHORTS_OPENAI_API_KEY` | — | OpenAI key. If empty, `OPENAI_API_KEY` is used. |
| `SHORTS_ELEVENLABS_API_KEY` | — | ElevenLabs key. Only needed with the `elevenlabs` transcriber. |
| `SHORTS_TRANSCRIBER` | `openai` | `openai` (whisper-1) or `elevenlabs` (Scribe). |
| `SHORTS_ELEVENLABS_MODEL` | `scribe_v2` | ElevenLabs speech-to-text model. |
| `SHORTS_SELECT_MODEL` | `gpt-6.1-sol` | OpenAI model that picks the clips. |
| `SHORTS_FFMPEG_BIN` | — | Path to ffmpeg. If empty: ffmpeg on your PATH, else the copy installed with the dependencies. |
| `SHORTS_SUBTITLE_FONT` | `Arial` | Caption font. For Russian or Kazakh it needs Cyrillic letters. |
| `SHORTS_SUBTITLE_SIZE` | `84` | Caption size on the 1080×1920 frame. |

## Use from Python

For the Content Factory worker, or any other code:

```python
from pathlib import Path

from shorts_cutter.pipeline import run

clips = run(Path("talk.mp4"), Path("out"), language="ru", count=5)
for clip in clips:
    print(clip.title, clip.start, clip.end, clip.score)
```

`run` takes the same options as the command line: `count`, `min_sec`, `max_sec`, `language`,
`transcriber`, `reframe`, `retranscribe`, `reselect`, and `render=False` for a dry run.

## Development

```bash
uv run pytest            # tests, including a real ffmpeg render of a generated video
uv run ruff check .      # lint
uv run ruff format .     # format
```

## Troubleshooting

| You see | Fix |
|---|---|
| `Failed to spawn: short-cutter` | The command is `shorts-cutter`, with an s. |
| `File '/demo/video.mp4' does not exist` | Drop the leading `/`. Paths are relative to the folder you are in. |
| An error mentioning `api_key`, or `401 Unauthorized` | Put a valid OpenAI key in `.env`. |
| `no speech found in …` | Clips are picked from what is said, so a video without speech can't be cut. |
| Fewer shorts than `--count` | Normal. The AI skips weak moments, and a clip that ends up shorter than `--min` after trimming to whole words is dropped. |
| Same clips after changing `--count`, `--min` or `--max` | Add `--reselect`. |
| Subtitles in another language than the speech | `--language` was not the spoken language, so it was translated. Run again with the right code and `--retranscribe`. |
| `--language` had no effect | The saved transcript was reused. Add `--retranscribe`. |
| Text or faces cut off at the sides | Use `--reframe blur`. `crop` keeps only the centre of a landscape frame. |
| Shorts look soft | The source is low resolution: a 720p video has only 405 px of width to crop from. Use `--reframe blur`, or a higher-resolution source. |
