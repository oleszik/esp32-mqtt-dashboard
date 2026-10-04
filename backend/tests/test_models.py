import pytest
from pydantic import ValidationError

from app.models import RuntimeConfig, Telemetry, parse_topic, validate_device_id


@pytest.mark.parametrize("value", ["esp32-demo-01", "a", "device_42"])
def test_valid_device_ids(value: str) -> None:
    assert validate_device_id(value) == value


@pytest.mark.parametrize("value", ["", "Upper", "bad/+", "a/b", "-leading", "a" * 65])
def test_invalid_device_ids(value: str) -> None:
    with pytest.raises(ValueError):
        validate_device_id(value)


def test_parse_topic_requires_exact_structure() -> None:
    assert parse_topic("iot/v1/devices/demo-1/telemetry") == ("demo-1", "telemetry")
    with pytest.raises(ValueError):
        parse_topic("iot/v1/devices/demo-1/telemetry/extra")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("temperature_c", 101),
        ("humidity_percent", -1),
        ("pressure_hpa", 1201),
        ("wifi_rssi_dbm", 1),
    ],
)
def test_telemetry_range_validation(telemetry: dict, field: str, value: float) -> None:
    telemetry[field] = value
    with pytest.raises(ValidationError):
        Telemetry.model_validate(telemetry)


def test_config_bounds() -> None:
    assert RuntimeConfig(schema_version=1, telemetry_interval_seconds=1)
    with pytest.raises(ValidationError):
        RuntimeConfig(schema_version=1, telemetry_interval_seconds=0)
