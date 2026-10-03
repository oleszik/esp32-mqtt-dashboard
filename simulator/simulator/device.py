import json
import math
import random
import re
import signal
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt

DEVICE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
UTC = timezone.utc  # noqa: UP017 - local verification also supports Python 3.10.


@dataclass(frozen=True)
class Sample:
    schema_version: int
    device_id: str
    boot_id: str
    sequence: int
    sampled_at: str
    uptime_seconds: int
    temperature_c: float
    humidity_percent: float
    pressure_hpa: float
    wifi_rssi_dbm: int

    def json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), allow_nan=False)


def generate_sample(
    device_id: str,
    boot_id: str,
    sequence: int,
    seed: int,
    sampled_at: datetime | None = None,
) -> Sample:
    rng = random.Random(seed + sequence * 104729)
    phase = sequence / 12.0
    return Sample(
        schema_version=1,
        device_id=device_id,
        boot_id=boot_id,
        sequence=sequence,
        sampled_at=(sampled_at or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
        uptime_seconds=sequence,
        temperature_c=round(22.5 + 2.4 * math.sin(phase) + rng.uniform(-0.12, 0.12), 2),
        humidity_percent=round(48.0 + 5.5 * math.sin(phase / 2 + 0.7) + rng.uniform(-0.2, 0.2), 2),
        pressure_hpa=round(1013.2 + 2.1 * math.sin(phase / 3 + 1.1) + rng.uniform(-0.08, 0.08), 2),
        wifi_rssi_dbm=round(-56 + 3 * math.sin(phase / 2) + rng.uniform(-1, 1)),
    )


class SimulatedDevice:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        device_id: str,
        interval: float,
        seed: int,
        boot_id: str | None = None,
    ) -> None:
        if not DEVICE_ID_PATTERN.fullmatch(device_id):
            raise ValueError("invalid device ID")
        self.host = host
        self.port = port
        self.device_id = device_id
        self.interval = interval
        self.seed = seed
        self.boot_id = boot_id or f"sim-{seed:08x}"
        self.connected = threading.Event()
        self.stop_event = threading.Event()
        self.telemetry_topic = f"iot/v1/devices/{device_id}/telemetry"
        self.status_topic = f"iot/v1/devices/{device_id}/status"
        self.config_topic = f"iot/v1/devices/{device_id}/config"
        self.ack_topic = f"iot/v1/devices/{device_id}/config/ack"
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"simulator-{device_id}",
        )
        self.client.username_pw_set(username, password)
        will = self._status("offline", "connection_lost")
        self.client.will_set(self.status_topic, will, qos=1, retain=True)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _status(self, status: str, reason: str) -> str:
        body: dict[str, Any] = {
            "schema_version": 1,
            "device_id": self.device_id,
            "status": status,
            "reason": reason,
        }
        if status == "online":
            body.update({"boot_id": self.boot_id, "firmware_version": "simulator-1.0.0"})
        return json.dumps(body, separators=(",", ":"))

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        del userdata, flags, properties
        if reason_code.is_failure:
            return
        client.publish(self.status_topic, self._status("online", "connected"), qos=1, retain=True)
        client.subscribe(self.config_topic, qos=1)
        self.connected.set()

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        del client, userdata, flags, reason_code, properties
        self.connected.clear()

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        del userdata
        result = "rejected"
        reason = "invalid configuration"
        interval: int | None = None
        try:
            document = json.loads(message.payload)
            candidate = document["telemetry_interval_seconds"]
            if (
                document.get("schema_version") == 1
                and isinstance(candidate, int)
                and 1 <= candidate <= 3600
            ):
                self.interval = float(candidate)
                interval = candidate
                result, reason = "applied", "configuration applied"
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        acknowledgement = {
            "schema_version": 1,
            "device_id": self.device_id,
            "boot_id": self.boot_id,
            "telemetry_interval_seconds": interval,
            "result": result,
            "reason": reason,
        }
        client.publish(
            self.ack_topic,
            json.dumps(acknowledgement, separators=(",", ":")),
            qos=1,
            retain=True,
        )

    def run(self, count: int | None = None, abrupt: bool = False) -> int:
        signal.signal(signal.SIGTERM, lambda *_: self.stop_event.set())
        signal.signal(signal.SIGINT, lambda *_: self.stop_event.set())
        self.client.connect(self.host, self.port, keepalive=30)
        self.client.loop_start()
        if not self.connected.wait(timeout=15):
            raise RuntimeError("MQTT connection timed out")
        sequence = 0
        try:
            while not self.stop_event.is_set() and (count is None or sequence < count):
                sample = generate_sample(self.device_id, self.boot_id, sequence, self.seed)
                info = self.client.publish(self.telemetry_topic, sample.json(), qos=1, retain=False)
                if info.wait_for_publish(timeout=10) is None and not info.is_published():
                    raise RuntimeError("telemetry publish timed out")
                print(sample.json(), flush=True)
                sequence += 1
                if count is None or sequence < count:
                    self.stop_event.wait(self.interval)
        finally:
            if abrupt:
                self.client._sock_close()  # Intentionally simulate transport loss for LWT tests.
                self.client.loop_stop()
            else:
                self.client.publish(
                    self.status_topic,
                    self._status("offline", "graceful_shutdown"),
                    qos=1,
                    retain=True,
                ).wait_for_publish(timeout=5)
                self.client.disconnect()
                self.client.loop_stop()
        return sequence
