from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any, Iterable


def _average(events: list[dict[str, Any]], field: str) -> float:
    values = [
        float(event[field])
        for event in events
        if isinstance(event.get(field), (int, float))
    ]
    return mean(values) if values else 0.0


def build_report(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = list(events)
    created = [event for event in items if event.get("event") == "MESSAGE_CREATED"]
    delivered = [
        event for event in items if event.get("event") == "PACKET_DELIVERED"
    ]
    dropped = [event for event in items if event.get("event") == "PACKET_DROPPED"]
    hops = [
        int(event["hop"])
        for event in delivered
        if isinstance(event.get("hop"), (int, float))
    ]
    reasons = Counter(
        str(event.get("drop_reason", "UNKNOWN")) for event in dropped
    )
    completed = len(delivered) + len(dropped)
    delivery_rate = len(delivered) / completed if completed else 0.0
    return {
        "events": len(items),
        "messages_created": len(created),
        "packets_delivered": len(delivered),
        "packets_dropped": len(dropped),
        "delivery_rate": delivery_rate,
        "average_hops": mean(hops) if hops else 0.0,
        "maximum_hops": max(hops, default=0),
        "average_latency_s": _average(delivered, "latency_s"),
        "average_rssi_dbm": _average(items, "rssi_dbm"),
        "average_snr_db": _average(items, "snr_db"),
        "drop_reasons": dict(reasons),
    }
