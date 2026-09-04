from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import SimulationConfig, ValidationError
from .runner import run_simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Executa uma rede mesh LoRa AU915")
    parser.add_argument("--nodes", type=int, default=10)
    parser.add_argument("--area-m", type=float, default=1000.0)
    parser.add_argument("--activation-min-s", type=float, default=0.0)
    parser.add_argument("--activation-max-s", type=float, default=3600.0)
    parser.add_argument("--simulation-time-s", type=float, default=14400.0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path("runs"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = SimulationConfig(
            node_count=args.nodes,
            area_m=args.area_m,
            activation_min_s=args.activation_min_s,
            activation_max_s=args.activation_max_s,
            simulation_time_s=args.simulation_time_s,
            seed=args.seed,
            output_dir=args.output_dir,
        )
    except ValidationError as error:
        print(f"Parâmetros inválidos: {error}")
        return 2
    result = run_simulation(config)
    print(
        json.dumps(
            {
                "success": result.success,
                "returncode": result.returncode,
                "output_dir": str(result.output_dir),
                "events": str(result.events_path),
                "report": str(result.report_path),
                "video": str(result.video_path) if result.video_path else None,
            },
            indent=2,
        )
    )
    return 0 if result.success else result.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
