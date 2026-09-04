from pathlib import Path
import os

from lora_mesh.video import (
    build_event_index,
    build_ffmpeg_command,
    frames_for_playback,
    latest_video,
    playback_duration_ms,
)


def test_event_index_has_one_scene_per_event(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        '{"time_s": 0, "event": "SIMULATION_STARTED"}\n'
        '{"time_s": 1, "event": "NODE_ACTIVATED", "node_id": "node[0]"}\n',
        encoding="utf-8",
    )
    index = build_event_index(events, event_duration_ms=300)
    assert len(index) == 2
    assert index[1]["duration_ms"] == 300


def test_ffmpeg_command_pads_mpeg2_and_uses_event_duration():
    command = build_ffmpeg_command(
        "ffmpeg",
        Path("frames") / "frame-%06d.png",
        Path("out") / "video.mpg",
        event_duration_ms=300,
    )
    assert command[command.index("-c:v") + 1] == "mpeg2video"
    assert command[command.index("-framerate") + 1] == "1000/300"
    assert "pad=ceil(iw/16)*16:ceil(ih/16)*16" in command
    assert str(command[-1]).endswith("video.mpg")


def test_frames_for_playback_resolves_mpg_and_run_dir(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    first = frames / "frame-000000.png"
    second = frames / "frame-000001.png"
    first.write_bytes(b"png")
    second.write_bytes(b"png")
    (tmp_path / "video.mpg").write_bytes(b"mpg")
    (tmp_path / "event-index.json").write_text(
        '[{"scene": 0, "duration_ms": 300}]\n', encoding="utf-8"
    )
    assert frames_for_playback(tmp_path / "video.mpg") == [first, second]
    assert frames_for_playback(tmp_path) == [first, second]
    assert playback_duration_ms(tmp_path / "video.mpg") == 300


def test_latest_video_picks_newest(tmp_path):
    older = tmp_path / "a"
    newer = tmp_path / "b"
    older.mkdir()
    newer.mkdir()
    first = older / "video.mpg"
    second = newer / "video.mpg"
    first.write_bytes(b"old")
    second.write_bytes(b"new")
    os.utime(first, (1_700_000_000, 1_700_000_000))
    os.utime(second, (1_800_000_000, 1_800_000_000))
    assert latest_video(tmp_path) == second
