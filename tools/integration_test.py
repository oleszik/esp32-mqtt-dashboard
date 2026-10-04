#!/usr/bin/env python3
"""Run the real simulator -> MQTT -> backend -> SQLite -> API integration test."""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8000"
DEVICE_ID = "esp32-demo-01"
COMPOSE_ENV = {
    **os.environ,
    "MQTT_DEVICE_USERNAME": "device",
    "MQTT_DEVICE_PASSWORD": "change-device-password",
    "MQTT_BACKEND_USERNAME": "backend",
    "MQTT_BACKEND_PASSWORD": "change-backend-password",
    "MQTT_TEST_USERNAME": "tester",
    "MQTT_TEST_PASSWORD": "change-test-password",
}


def run(*args: str, capture: bool = False) -> str:
    command = ["docker", "compose", *args]
    print("+", " ".join(command), flush=True)
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=capture,
        env=COMPOSE_ENV,
    )
    return result.stdout if capture else ""


def request(path: str, timeout: float = 3) -> object:
    with urllib.request.urlopen(BASE_URL + path, timeout=timeout) as response:
        return json.load(response)


def wait_for(path: str, predicate, timeout: int = 60):
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            result = request(path)
            if predicate(result):
                return result
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = exc
        time.sleep(1)
    raise AssertionError(f"timed out waiting for {path}; last error: {last_error}")


def main() -> int:
    evidence: list[str] = []
    run("--profile", "demo", "down", "--volumes", "--remove-orphans")
    try:
        run("build", "broker", "backend", "simulator")
        run("up", "-d", "broker", "backend")
        health = wait_for("/api/health", lambda body: body.get("mqtt") == "connected")
        evidence.append(f"backend health: {health}")

        output = run(
            "run",
            "--rm",
            "--no-deps",
            "simulator",
            "--count",
            "5",
            "--interval",
            "0.05",
            capture=True,
        )
        sample_lines = [line for line in output.splitlines() if line.startswith("{")]
        assert len(sample_lines) == 5, output
        first = json.loads(sample_lines[0])
        assert first["sequence"] == 0
        assert first["temperature_c"] == 22.53
        evidence.append(
            f"first deterministic telemetry: {json.dumps(first, sort_keys=True)}"
        )

        wait_for(
            f"/api/devices/{DEVICE_ID}", lambda body: body.get("message_count", 0) >= 5
        )
        history = request(f"/api/devices/{DEVICE_ID}/telemetry?limit=10")
        assert len(history) >= 5
        assert [item["sequence"] for item in history[-5:]] == [0, 1, 2, 3, 4]
        evidence.append(f"persisted telemetry count: {len(history)}")

        malformed = "iot/v1/devices/esp32-demo-01/telemetry"
        run(
            "exec",
            "-T",
            "broker",
            "mosquitto_pub",
            "-h",
            "127.0.0.1",
            "-u",
            "tester",
            "-P",
            "change-test-password",
            "-q",
            "1",
            "-t",
            malformed,
            "-m",
            "not-json",
        )
        rejected = wait_for(
            f"/api/devices/{DEVICE_ID}", lambda body: body.get("rejected_count", 0) >= 1
        )
        assert rejected["rejected_count"] >= 1
        assert request("/api/health")["status"] == "healthy"
        evidence.append("malformed payload rejected; backend remained healthy")

        run(
            "run",
            "--rm",
            "--no-deps",
            "simulator",
            "--count",
            "1",
            "--interval",
            "0.05",
            "--abrupt",
        )
        offline = wait_for(
            f"/api/devices/{DEVICE_ID}",
            lambda body: body.get("status") == "offline"
            and body.get("status_reason") == "connection_lost",
            timeout=45,
        )
        evidence.append(f"LWT status: {offline['status']} ({offline['status_reason']})")

        before_restart = len(request(f"/api/devices/{DEVICE_ID}/telemetry?limit=100"))
        run("restart", "backend")
        wait_for("/api/health", lambda body: body.get("mqtt") == "connected")
        after_restart = len(request(f"/api/devices/{DEVICE_ID}/telemetry?limit=100"))
        assert after_restart == before_restart
        evidence.append(f"persistence after backend restart: {after_restart} records")

        page = urllib.request.urlopen(BASE_URL, timeout=3).read().decode()
        assert "ESP32 MQTT Monitor" in page
        evidence.append("dashboard HTML served successfully")

        destination = ROOT / "docs" / "integration-test-output.txt"
        destination.write_text("\n".join(evidence) + "\n", encoding="utf-8")
        print("INTEGRATION TEST PASSED")
        return 0
    finally:
        run("--profile", "demo", "down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    sys.exit(main())
