from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Sequence

from .config import SimulationConfig
from .events import read_events
from .report import build_report
from .video import render_events


@dataclass(frozen=True)
class RunResult:
    success: bool
    returncode: int
    output_dir: Path
    log_path: Path
    events_path: Path
    report_path: Path
    video_path: Path | None


def run_command(
    command: Sequence[str],
    cwd: Path,
    log_path: Path,
    cancel_event: Event | None = None,
) -> subprocess.CompletedProcess[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(command) + "\n")
        log.flush()
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        while process.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                log.write("Cancelamento solicitado pelo usuário.\n")
                log.flush()
                break
            time.sleep(0.05)
        returncode = process.wait()
    return subprocess.CompletedProcess(command, returncode)


def _new_output_dir(root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = root / stamp
    suffix = 1
    while candidate.exists():
        candidate = root / f"{stamp}-{suffix}"
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def run_simulation(
    config: SimulationConfig, cancel_event: Event | None = None
) -> RunResult:
    output_dir = _new_output_dir(Path(config.output_dir))
    scenario_path = output_dir / "scenario.ini"
    log_path = output_dir / "run.log"
    events_path = output_dir / "events.jsonl"
    report_path = output_dir / "report.json"
    run_config = replace(config, output_dir=output_dir)
    run_config.write_ini(scenario_path)
    config.write_json(output_dir / "parameters.json")

    simulator = Path(
        os.environ.get(
            "LORA_MESH_SIMULATOR",
            Path(__file__).parents[2]
            / "simulations"
            / "LoRaMesh"
            / "out"
            / "LoRaMesh",
        )
    )
    if not simulator.exists():
        log_path.write_text(
            f"Executável não encontrado: {simulator}\n"
            "Compile simulations/LoRaMesh antes de executar.\n",
            encoding="utf-8",
        )
        return RunResult(
            False, 127, output_dir, log_path, events_path, report_path, None
        )

    command = [
        str(simulator),
        "-u",
        "Cmdenv",
        "-c",
        "Mesh",
        "-n",
        ":".join(
            filter(
                None,
                [
                    str(simulator.parent.parent),
                    str(Path(os.environ["INET_ROOT"]) / "src")
                    if os.environ.get("INET_ROOT")
                    else "",
                    str(Path(os.environ["FLORA_ROOT"]) / "src")
                    if os.environ.get("FLORA_ROOT")
                    else "",
                ],
            )
        ),
        "-f",
        str(scenario_path.resolve()),
    ]
    completed = run_command(command, simulator.parent, log_path, cancel_event)
    if completed.returncode != 0 or not events_path.exists():
        return RunResult(
            False,
            completed.returncode,
            output_dir,
            log_path,
            events_path,
            report_path,
            None,
        )

    report = build_report(read_events(events_path))
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    video_path = render_events(events_path, output_dir, area_m=config.area_m)
    return RunResult(
        True,
        completed.returncode,
        output_dir,
        log_path,
        events_path,
        report_path,
        video_path,
    )
