from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator


class EventLogger:
    """Escritor incremental do contrato JSONL de eventos."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("w", encoding="utf-8")

    def write(self, event: dict[str, Any]) -> None:
        if not isinstance(event, dict) or "event" not in event:
            raise ValueError("todo evento deve ser um objeto com o campo event")
        self._stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        self._stream.flush()

    def close(self) -> None:
        if not self._stream.closed:
            self._stream.close()

    def __enter__(self) -> "EventLogger":
        return self

    def __exit__(self, _type: Any, _value: Any, _traceback: Any) -> None:
        self.close()


def iter_events(path: Path) -> Iterator[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"JSON inválido na linha {line_number}") from error
            if not isinstance(event, dict):
                raise ValueError(f"o evento da linha {line_number} não é um objeto")
            yield event


def read_events(path: Path) -> list[dict[str, Any]]:
    return list(iter_events(path))


def event_names(events: Iterable[dict[str, Any]]) -> list[str]:
    return [str(event["event"]) for event in events if "event" in event]
