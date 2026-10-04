import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import ConfigAck, DeviceStatus, Telemetry

UTC = timezone.utc  # noqa: UP017 - local verification also supports Python 3.10.


def utc_now() -> datetime:
    return datetime.now(UTC)


def isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class Repository:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'unknown',
                    status_reason TEXT,
                    firmware_version TEXT,
                    boot_id TEXT,
                    latest_sequence INTEGER,
                    last_seen TEXT,
                    last_telemetry_at TEXT,
                    message_count INTEGER NOT NULL DEFAULT 0,
                    duplicate_count INTEGER NOT NULL DEFAULT 0,
                    rejected_count INTEGER NOT NULL DEFAULT 0,
                    latest_telemetry_json TEXT
                );
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    boot_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    sampled_at TEXT,
                    received_at TEXT NOT NULL,
                    uptime_seconds INTEGER NOT NULL,
                    temperature_c REAL NOT NULL,
                    humidity_percent REAL NOT NULL,
                    pressure_hpa REAL NOT NULL,
                    wifi_rssi_dbm INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE(device_id, boot_id, sequence)
                );
                CREATE INDEX IF NOT EXISTS idx_telemetry_device_received
                    ON telemetry(device_id, received_at DESC);
                CREATE TABLE IF NOT EXISTS status_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS config_acks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    result TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rejected_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT,
                    topic TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    payload_size INTEGER NOT NULL,
                    received_at TEXT NOT NULL
                );
                """
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def ping(self) -> bool:
        with self._lock:
            return self._connection.execute("SELECT 1").fetchone()[0] == 1

    def store_telemetry(self, telemetry: Telemetry, received_at: datetime) -> bool:
        received = isoformat(received_at)
        payload = telemetry.model_dump_json()
        with self._lock, self._connection:
            self._ensure_device(telemetry.device_id)
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO telemetry (
                    device_id, boot_id, sequence, sampled_at, received_at,
                    uptime_seconds, temperature_c, humidity_percent,
                    pressure_hpa, wifi_rssi_dbm, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telemetry.device_id,
                    telemetry.boot_id,
                    telemetry.sequence,
                    isoformat(telemetry.sampled_at) if telemetry.sampled_at else None,
                    received,
                    telemetry.uptime_seconds,
                    telemetry.temperature_c,
                    telemetry.humidity_percent,
                    telemetry.pressure_hpa,
                    telemetry.wifi_rssi_dbm,
                    payload,
                ),
            )
            inserted = cursor.rowcount == 1
            if inserted:
                self._connection.execute(
                    """
                    UPDATE devices SET boot_id=?, latest_sequence=?, last_seen=?,
                        last_telemetry_at=?, message_count=message_count+1,
                        latest_telemetry_json=? WHERE device_id=?
                    """,
                    (
                        telemetry.boot_id,
                        telemetry.sequence,
                        received,
                        received,
                        payload,
                        telemetry.device_id,
                    ),
                )
            else:
                self._connection.execute(
                    "UPDATE devices SET duplicate_count=duplicate_count+1 WHERE device_id=?",
                    (telemetry.device_id,),
                )
            return inserted

    def store_status(self, status: DeviceStatus, received_at: datetime) -> None:
        received = isoformat(received_at)
        payload = status.model_dump_json(exclude_none=True)
        with self._lock, self._connection:
            self._ensure_device(status.device_id)
            self._connection.execute(
                """
                UPDATE devices SET status=?, status_reason=?,
                    firmware_version=COALESCE(?, firmware_version),
                    boot_id=COALESCE(?, boot_id), last_seen=? WHERE device_id=?
                """,
                (
                    status.status,
                    status.reason,
                    status.firmware_version,
                    status.boot_id,
                    received,
                    status.device_id,
                ),
            )
            self._connection.execute(
                """INSERT INTO status_events
                (device_id, status, reason, received_at, payload_json)
                VALUES (?, ?, ?, ?, ?)""",
                (status.device_id, status.status, status.reason, received, payload),
            )

    def store_config_ack(self, ack: ConfigAck, received_at: datetime) -> None:
        received = isoformat(received_at)
        with self._lock, self._connection:
            self._ensure_device(ack.device_id)
            self._connection.execute(
                """INSERT INTO config_acks
                (device_id, result, received_at, payload_json) VALUES (?, ?, ?, ?)""",
                (ack.device_id, ack.result, received, ack.model_dump_json(exclude_none=True)),
            )

    def record_rejection(
        self,
        topic: str,
        reason: str,
        payload_size: int,
        received_at: datetime,
        device_id: str | None = None,
    ) -> None:
        safe_reason = reason[:256]
        with self._lock, self._connection:
            if device_id:
                self._ensure_device(device_id)
                self._connection.execute(
                    "UPDATE devices SET rejected_count=rejected_count+1 WHERE device_id=?",
                    (device_id,),
                )
            self._connection.execute(
                """INSERT INTO rejected_messages
                (device_id, topic, reason, payload_size, received_at)
                VALUES (?, ?, ?, ?, ?)""",
                (device_id, topic[:256], safe_reason, payload_size, isoformat(received_at)),
            )

    def _ensure_device(self, device_id: str) -> None:
        self._connection.execute(
            "INSERT OR IGNORE INTO devices(device_id) VALUES (?)", (device_id,)
        )

    def list_devices(self, stale_after_seconds: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute("SELECT * FROM devices ORDER BY device_id").fetchall()
        return [self._device_dict(row, stale_after_seconds) for row in rows]

    def get_device(self, device_id: str, stale_after_seconds: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM devices WHERE device_id=?", (device_id,)
            ).fetchone()
        return self._device_dict(row, stale_after_seconds) if row else None

    def _device_dict(self, row: sqlite3.Row, stale_after_seconds: int) -> dict[str, Any]:
        result = dict(row)
        latest = result.pop("latest_telemetry_json")
        result["latest_telemetry"] = json.loads(latest) if latest else None
        last_telemetry = result.get("last_telemetry_at")
        threshold = utc_now() - timedelta(seconds=stale_after_seconds)
        result["stale"] = (
            not last_telemetry
            or datetime.fromisoformat(last_telemetry.replace("Z", "+00:00")) < threshold
        )
        return result

    def telemetry_history(self, device_id: str, limit: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT payload_json, received_at FROM telemetry
                WHERE device_id=? ORDER BY id DESC LIMIT ?
                """,
                (device_id, limit),
            ).fetchall()
        result = []
        for row in reversed(rows):
            item = json.loads(row["payload_json"])
            item["received_at"] = row["received_at"]
            result.append(item)
        return result

    def recent_events(self, limit: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT 'status' AS event_type, device_id, status || ': ' || reason AS detail,
                       received_at FROM status_events
                UNION ALL
                SELECT 'config_ack', device_id, result, received_at FROM config_acks
                UNION ALL
                SELECT 'rejected', device_id, reason, received_at FROM rejected_messages
                ORDER BY received_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def rejection_count(self) -> int:
        with self._lock:
            return self._connection.execute("SELECT COUNT(*) FROM rejected_messages").fetchone()[0]
