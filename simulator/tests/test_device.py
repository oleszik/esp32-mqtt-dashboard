from datetime import datetime, timezone

from simulator import generate_sample

UTC = timezone.utc  # noqa: UP017 - local verification also supports Python 3.10.


def test_sample_is_deterministic() -> None:
    timestamp = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    first = generate_sample("esp32-demo-01", "boot-a", 0, 42, timestamp)
    second = generate_sample("esp32-demo-01", "boot-a", 0, 42, timestamp)
    assert first == second
    assert first.temperature_c == 22.53
    assert first.humidity_percent == 51.35
    assert first.pressure_hpa == 1015.04
    assert first.wifi_rssi_dbm == -57


def test_sequence_changes_waveform() -> None:
    timestamp = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    one = generate_sample("esp32-demo-01", "boot-a", 1, 42, timestamp)
    two = generate_sample("esp32-demo-01", "boot-a", 2, 42, timestamp)
    assert one.temperature_c != two.temperature_c
    assert 0 <= one.humidity_percent <= 100
    assert 300 <= one.pressure_hpa <= 1200
