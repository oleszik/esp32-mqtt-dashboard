import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(database_path=tmp_path / "test.db", mqtt_enabled=False, stale_after_seconds=10)


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def telemetry() -> dict:
    return {
        "schema_version": 1,
        "device_id": "esp32-demo-01",
        "boot_id": "boot-a",
        "sequence": 0,
        "sampled_at": "2026-10-03T15:30:12Z",
        "uptime_seconds": 10,
        "temperature_c": 22.4,
        "humidity_percent": 48.1,
        "pressure_hpa": 1013.2,
        "wifi_rssi_dbm": -56,
    }
