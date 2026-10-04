#!/usr/bin/env python3
"""Generate sanitized documentation examples through production schema code."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "simulator"))

from app.models import DeviceStatus, Telemetry  # noqa: E402
from simulator import generate_sample  # noqa: E402

UTC = timezone.utc  # noqa: UP017 - script also runs with the local Python 3.10.


def write_json(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    sample = generate_sample(
        "esp32-demo-01",
        "sim-0000002a",
        0,
        42,
        datetime(2026, 10, 3, 12, 0, tzinfo=UTC),
    )
    telemetry = Telemetry.model_validate(json.loads(sample.json()))
    status = DeviceStatus(
        schema_version=1,
        device_id="esp32-demo-01",
        boot_id="sim-0000002a",
        status="online",
        reason="connected",
        firmware_version="simulator-1.0.0",
    )
    write_json(docs / "example-telemetry.json", telemetry.model_dump(mode="json"))
    write_json(
        docs / "example-status.json", status.model_dump(mode="json", exclude_none=True)
    )
    print("Generated validated telemetry and status examples.")


if __name__ == "__main__":
    main()
