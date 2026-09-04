import os
from pathlib import Path

import pytest

from lora_mesh.events import read_events


@pytest.fixture
def minimal_run() -> Path:
    configured = os.environ.get("LORA_MESH_MINIMAL_RUN")
    if not configured:
        pytest.skip("defina LORA_MESH_MINIMAL_RUN após executar o cenário mínimo")
    path = Path(configured)
    if not (path / "events.jsonl").exists():
        pytest.skip(f"events.jsonl não encontrado em {path}")
    return path


def test_minimal_run_contains_lifecycle_and_activation(minimal_run):
    events = read_events(minimal_run / "events.jsonl")
    names = [event["event"] for event in events]
    assert names[0] == "SIMULATION_STARTED"
    assert "NODE_ACTIVATED" in names
    assert names[-1] == "SIMULATION_FINISHED"
