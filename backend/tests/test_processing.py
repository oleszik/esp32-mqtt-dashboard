import json
from datetime import datetime, timezone

from app.repository import Repository
from app.services import MessageProcessor

UTC = timezone.utc  # noqa: UP017 - local verification also supports Python 3.10.


def payload(document: dict) -> bytes:
    return json.dumps(document, separators=(",", ":")).encode()


def test_process_telemetry_and_duplicate(tmp_path, telemetry: dict) -> None:
    repository = Repository(tmp_path / "db.sqlite")
    processor = MessageProcessor(repository)
    topic = "iot/v1/devices/esp32-demo-01/telemetry"
    assert processor.process(topic, payload(telemetry)) is True
    assert processor.process(topic, payload(telemetry)) is False
    device = repository.get_device("esp32-demo-01", 10)
    assert device["message_count"] == 1
    assert device["duplicate_count"] == 1
    assert len(repository.telemetry_history("esp32-demo-01", 10)) == 1


def test_rejects_malformed_nonfinite_and_mismatch(tmp_path, telemetry: dict) -> None:
    repository = Repository(tmp_path / "db.sqlite")
    processor = MessageProcessor(repository, max_payload_bytes=1024)
    topic = "iot/v1/devices/esp32-demo-01/telemetry"
    assert processor.process(topic, b"not-json") is False
    assert processor.process(topic, payload({**telemetry, "temperature_c": float("nan")})) is False
    assert processor.process(topic, payload({**telemetry, "device_id": "other"})) is False
    assert repository.rejection_count() == 3


def test_rejects_oversized_payload(tmp_path) -> None:
    repository = Repository(tmp_path / "db.sqlite")
    processor = MessageProcessor(repository, max_payload_bytes=256)
    assert processor.process("iot/v1/devices/demo/telemetry", b"x" * 257) is False


def test_status_and_stale_calculation(tmp_path) -> None:
    repository = Repository(tmp_path / "db.sqlite")
    repository.store_status(
        __import__("app.models", fromlist=["DeviceStatus"]).DeviceStatus(
            schema_version=1,
            device_id="demo",
            boot_id="boot-a",
            status="online",
            reason="connected",
        ),
        datetime.now(UTC),
    )
    device = repository.get_device("demo", 10)
    assert device["status"] == "online"
    assert device["stale"] is True


def test_history_order(tmp_path, telemetry: dict) -> None:
    repository = Repository(tmp_path / "db.sqlite")
    processor = MessageProcessor(repository)
    topic = "iot/v1/devices/esp32-demo-01/telemetry"
    for sequence in range(3):
        processor.process(topic, payload({**telemetry, "sequence": sequence}))
    assert [row["sequence"] for row in repository.telemetry_history("esp32-demo-01", 2)] == [1, 2]
