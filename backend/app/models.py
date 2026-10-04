import math
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEVICE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
BOOT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
TOPIC_PATTERN = re.compile(
    r"^iot/v1/devices/(?P<device_id>[a-z0-9][a-z0-9_-]{0,63})/"
    r"(?P<kind>telemetry|status|config/ack)$"
)
MIN_TELEMETRY_INTERVAL_SECONDS = 1
MAX_TELEMETRY_INTERVAL_SECONDS = 3600


def validate_device_id(value: str) -> str:
    if not DEVICE_ID_PATTERN.fullmatch(value):
        raise ValueError("invalid device_id")
    return value


def parse_topic(topic: str) -> tuple[str, str]:
    match = TOPIC_PATTERN.fullmatch(topic)
    if not match:
        raise ValueError("invalid MQTT topic")
    return match.group("device_id"), match.group("kind")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Telemetry(StrictModel):
    schema_version: Literal[1]
    device_id: str
    boot_id: str
    sequence: int = Field(ge=0, le=2**63 - 1)
    sampled_at: datetime | None
    uptime_seconds: int = Field(ge=0, le=2**32 - 1)
    temperature_c: float = Field(ge=-50.0, le=100.0)
    humidity_percent: float = Field(ge=0.0, le=100.0)
    pressure_hpa: float = Field(ge=300.0, le=1200.0)
    wifi_rssi_dbm: int = Field(ge=-127, le=0)

    @field_validator("device_id")
    @classmethod
    def valid_device_id(cls, value: str) -> str:
        return validate_device_id(value)

    @field_validator("boot_id")
    @classmethod
    def valid_boot_id(cls, value: str) -> str:
        if not BOOT_ID_PATTERN.fullmatch(value):
            raise ValueError("invalid boot_id")
        return value

    @field_validator("temperature_c", "humidity_percent", "pressure_hpa")
    @classmethod
    def finite_number(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("measurement must be finite")
        return value


class DeviceStatus(StrictModel):
    schema_version: Literal[1]
    device_id: str
    boot_id: str | None = None
    status: Literal["online", "offline"]
    reason: str = Field(min_length=1, max_length=64)
    firmware_version: str | None = Field(default=None, max_length=32)

    @field_validator("device_id")
    @classmethod
    def valid_device_id(cls, value: str) -> str:
        return validate_device_id(value)

    @field_validator("boot_id")
    @classmethod
    def valid_boot_id(cls, value: str | None) -> str | None:
        if value is not None and not BOOT_ID_PATTERN.fullmatch(value):
            raise ValueError("invalid boot_id")
        return value


class ConfigAck(StrictModel):
    schema_version: Literal[1]
    device_id: str
    boot_id: str
    telemetry_interval_seconds: int | None = Field(
        default=None,
        ge=MIN_TELEMETRY_INTERVAL_SECONDS,
        le=MAX_TELEMETRY_INTERVAL_SECONDS,
    )
    result: Literal["applied", "rejected"]
    reason: str | None = Field(default=None, max_length=128)

    @field_validator("device_id")
    @classmethod
    def valid_device_id(cls, value: str) -> str:
        return validate_device_id(value)


class RuntimeConfig(StrictModel):
    schema_version: Literal[1]
    telemetry_interval_seconds: int = Field(
        ge=MIN_TELEMETRY_INTERVAL_SECONDS,
        le=MAX_TELEMETRY_INTERVAL_SECONDS,
    )
