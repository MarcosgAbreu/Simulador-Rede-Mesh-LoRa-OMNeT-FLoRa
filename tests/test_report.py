from lora_mesh.report import build_report


def test_report_counts_delivery_and_loss():
    report = build_report(
        [
            {"event": "MESSAGE_CREATED"},
            {"event": "PACKET_DELIVERED", "hop": 3, "latency_s": 1.5},
            {"event": "PACKET_DROPPED", "drop_reason": "TTL_EXPIRED"},
        ]
    )
    assert report["messages_created"] == 1
    assert report["packets_delivered"] == 1
    assert report["packets_dropped"] == 1
    assert report["delivery_rate"] == 0.5
