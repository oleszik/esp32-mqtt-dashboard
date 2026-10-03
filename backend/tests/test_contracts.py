import json
from pathlib import Path

from app.models import DeviceStatus, Telemetry

CONTRACTS = Path(__file__).parents[2] / "tests" / "contracts"


def test_shared_telemetry_fixture() -> None:
    document = json.loads((CONTRACTS / "telemetry.json").read_text())
    assert Telemetry.model_validate(document).sequence == 42


def test_shared_status_fixture() -> None:
    document = json.loads((CONTRACTS / "status-online.json").read_text())
    assert DeviceStatus.model_validate(document).status == "online"
