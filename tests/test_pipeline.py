"""End to end with real ffmpeg on a synthetic video; only the two API calls are stubbed."""

import json
import subprocess

import pytest

from shorts_cutter import media, pipeline, selector
from shorts_cutter.models import Clip, Segment, Transcript, Word


@pytest.fixture
def video(tmp_path):
    path = tmp_path / "talk.mp4"
    media.run_ffmpeg([
        "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=25:duration=12",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=12",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(path),
    ])  # fmt: skip
    return path


@pytest.fixture
def stub_apis(monkeypatch):
    words = [Word(text=f"слово{i}", start=i * 0.5, end=i * 0.5 + 0.4) for i in range(24)]
    transcript = Transcript(language="ru", words=words, segments=[Segment(text="…", start=0, end=11.9)])
    monkeypatch.setattr(pipeline, "transcribe", lambda audio, **_: transcript)
    monkeypatch.setattr(
        selector,
        "_ask_model",
        lambda *_, **__: [
            Clip(start=1.0, end=5.4, title="Первый", hook="h", reason="r", score=8),
            Clip(start=6.0, end=10.4, title="Второй", hook="h", reason="r", score=6),
        ],
    )


@pytest.mark.parametrize("reframe", ["crop", "blur"])
def test_renders_vertical_shorts_with_subtitles(tmp_path, video, stub_apis, reframe):
    clips = pipeline.run(video, tmp_path / "out", min_sec=3, max_sec=6, reframe=reframe)
    work = tmp_path / "out" / "talk"

    assert [c.title for c in clips] == ["Первый", "Второй"]
    manifest = json.loads((work / "clips.json").read_text())
    assert [m["file"] for m in manifest] == ["clip_01.mp4", "clip_02.mp4"]
    assert "слово2" in (work / "clip_01.srt").read_text()

    probe = subprocess.run(
        [media.ffmpeg_bin(), "-hide_banner", "-i", str(work / "clip_01.mp4")], capture_output=True, text=True
    ).stderr
    assert "1080x1920" in probe
    assert "Audio: aac" in probe


def test_render_after_dry_run_uses_reviewed_clips(tmp_path, video, stub_apis, monkeypatch):
    pipeline.run(video, tmp_path / "out", min_sec=3, max_sec=6, render=False)
    work = tmp_path / "out" / "talk"
    assert not list(work.glob("clip_*"))

    # The reviewer deletes the first clip by hand; rendering must not ask the model again.
    manifest = json.loads((work / "clips.json").read_text())
    (work / "clips.json").write_text(json.dumps(manifest[1:]))
    monkeypatch.setattr(selector, "_ask_model", lambda *_, **__: pytest.fail("model called again"))

    clips = pipeline.run(video, tmp_path / "out", min_sec=3, max_sec=6)
    assert [c.title for c in clips] == ["Второй"]
    assert (work / "clip_01.mp4").exists()
    assert not (work / "clip_02.mp4").exists()
    assert json.loads((work / "clips.json").read_text())[0]["file"] == "clip_01.mp4"
