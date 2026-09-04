from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .events import read_events

EVENT_DURATION_MS = 300
_VIDEO_SUFFIXES = {".mpg", ".mpeg", ".mp4", ".mpeg2"}


def frames_for_playback(path: Path) -> list[Path]:
    resolved = Path(path).expanduser()
    if resolved.is_file() and resolved.suffix.lower() in _VIDEO_SUFFIXES:
        resolved = resolved.parent
    if (resolved / "frames").is_dir():
        resolved = resolved / "frames"
    if not resolved.is_dir():
        return []
    return sorted(resolved.glob("frame-*.png"))


def playback_duration_ms(path: Path, default: int = EVENT_DURATION_MS) -> int:
    directory = Path(path)
    if directory.is_file():
        directory = directory.parent
    index_path = directory / "event-index.json"
    if not index_path.is_file():
        return default
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default
    if not payload:
        return default
    duration = payload[0].get("duration_ms", default)
    try:
        value = int(duration)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def latest_video(root: Path = Path("runs")) -> Path | None:
    root = Path(root)
    if not root.exists():
        return None
    videos = [path for path in root.rglob("video.mpg") if path.is_file()]
    if not videos:
        return None
    return max(videos, key=lambda path: path.stat().st_mtime)


def build_ffmpeg_command(
    ffmpeg: str,
    frames_pattern: Path,
    video_path: Path,
    event_duration_ms: int = EVENT_DURATION_MS,
) -> list[str]:
    if event_duration_ms <= 0:
        raise ValueError("event_duration_ms deve ser maior que zero")
    return [
        ffmpeg,
        "-y",
        "-framerate",
        f"1000/{event_duration_ms}",
        "-i",
        str(frames_pattern),
        "-vf",
        "pad=ceil(iw/16)*16:ceil(ih/16)*16",
        "-c:v",
        "mpeg2video",
        "-q:v",
        "4",
        "-pix_fmt",
        "yuv420p",
        "-muxpreload",
        "0",
        "-muxdelay",
        "0",
        str(video_path),
    ]


def open_with_ffplay(video_path: Path) -> subprocess.Popen[str]:
    ffplay = shutil.which("ffplay")
    if ffplay is None:
        raise RuntimeError("ffplay não encontrado; instale ffmpeg")
    return subprocess.Popen(
        [
            ffplay,
            "-autoexit",
            "-loglevel",
            "warning",
            "-window_title",
            video_path.name,
            str(video_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def build_event_index(events_path: Path, event_duration_ms: int = 300) -> list[dict[str, Any]]:
    if event_duration_ms <= 0:
        raise ValueError("event_duration_ms deve ser maior que zero")
    return [
        {
            "scene": index,
            "time_s": event.get("time_s", 0.0),
            "event": event.get("event", "UNKNOWN"),
            "duration_ms": event_duration_ms,
        }
        for index, event in enumerate(read_events(events_path))
    ]


def _draw_frame(
    event: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    links: list[tuple[str, str]],
    path: Path,
    area_m: float,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(10, 7), dpi=100)
    axis.set_xlim(0, area_m)
    axis.set_ylim(0, area_m)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("x (m)")
    axis.set_ylabel("y (m)")
    axis.set_title(
        f"{event.get('event', 'UNKNOWN')} | t={float(event.get('time_s', 0.0)):.3f} s"
    )

    for left, right in links:
        first = nodes.get(left, {}).get("position_m")
        second = nodes.get(right, {}).get("position_m")
        if first and second:
            axis.plot(
                [first["x"], second["x"]],
                [first["y"], second["y"]],
                color="tab:orange",
                linewidth=1.5,
                alpha=0.8,
            )

    active_x = []
    active_y = []
    inactive_x = []
    inactive_y = []
    for state in nodes.values():
        position = state.get("position_m")
        if not position:
            continue
        target_x = active_x if state.get("active") else inactive_x
        target_y = active_y if state.get("active") else inactive_y
        target_x.append(position["x"])
        target_y.append(position["y"])
    if inactive_x:
        axis.scatter(inactive_x, inactive_y, color="lightgray", label="inativo")
    if active_x:
        axis.scatter(active_x, active_y, color="tab:blue", label="ativo")
    axis.scatter([area_m / 2], [area_m / 2], marker="*", s=180, color="tab:red", label="gateway")
    if active_x or inactive_x:
        axis.legend(loc="upper right")

    details = [
        f"nodo: {event.get('node_id', '-')}",
        f"mensagem: {event.get('message_id', '-')}",
        f"salto: {event.get('hop', '-')}",
        f"status: {event.get('status', '-')}",
    ]
    figure.text(0.02, 0.02, " | ".join(details), fontsize=9)
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)


def render_events(
    events_path: Path,
    output_dir: Path,
    event_duration_ms: int = 300,
    area_m: float = 1000.0,
) -> Path:
    output_dir = Path(output_dir)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    events = read_events(events_path)
    if not events:
        raise ValueError("não há eventos para renderizar")
    index = build_event_index(events_path, event_duration_ms)
    nodes: dict[str, dict[str, Any]] = {}
    links: list[tuple[str, str]] = []
    for scene, event in zip(index, events):
        node_id = event.get("node_id")
        if node_id:
            state = nodes.setdefault(str(node_id), {})
            if "position_m" in event:
                state["position_m"] = event["position_m"]
            if event.get("event") == "NODE_ACTIVATED":
                state["active"] = True
        source_id = event.get("source_id")
        next_hop_id = event.get("next_hop_id")
        if source_id and next_hop_id:
            link = (str(source_id), str(next_hop_id))
            if link not in links:
                links.append(link)
        frame_path = frames_dir / f"frame-{scene['scene']:06d}.png"
        _draw_frame(event, nodes, links, frame_path, area_m)
        scene["frame"] = str(frame_path.relative_to(output_dir))

    index_path = output_dir / "event-index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    video_path = output_dir / "video.mpg"
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg não encontrado; execute scripts/install_wsl2.sh")
    command = build_ffmpeg_command(
        ffmpeg,
        frames_dir / "frame-%06d.png",
        video_path,
        event_duration_ms,
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"falha ao gerar MPEG:\n{completed.stderr}")
    return video_path
