from lora_mesh.events import EventLogger, read_events


def test_logger_writes_one_json_object_per_line(tmp_path):
    path = tmp_path / "events.jsonl"
    logger = EventLogger(path)
    logger.write({"time_s": 1.0, "event": "NODE_ACTIVATED", "node_id": "node[0]"})
    logger.close()
    assert read_events(path) == [
        {"time_s": 1.0, "event": "NODE_ACTIVATED", "node_id": "node[0]"}
    ]
