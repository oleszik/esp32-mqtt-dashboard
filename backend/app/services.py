import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from .models import ConfigAck, DeviceStatus, Telemetry, parse_topic
from .repository import Repository

logger = logging.getLogger(__name__)
UTC = timezone.utc  # noqa: UP017 - local verification also supports Python 3.10.


class MessageProcessor:
    def __init__(
        self,
        repository: Repository,
        max_payload_bytes: int = 4096,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.repository = repository
        self.max_payload_bytes = max_payload_bytes
        self.event_callback = event_callback

    def process(self, topic: str, payload: bytes) -> bool:
        received_at = datetime.now(UTC)
        device_id: str | None = None
        try:
            device_id, kind = parse_topic(topic)
            if len(payload) > self.max_payload_bytes:
                raise ValueError("payload exceeds configured size limit")
            document = json.loads(payload, parse_constant=self._reject_constant)
            if not isinstance(document, dict):
                raise ValueError("payload must be a JSON object")
            if document.get("device_id") != device_id:
                raise ValueError("topic and payload device_id do not match")
            if kind == "telemetry":
                model = Telemetry.model_validate(document)
                inserted = self.repository.store_telemetry(model, received_at)
                if inserted:
                    self._emit("telemetry", model.model_dump(mode="json"), received_at)
                    logger.info(
                        "accepted telemetry device=%s sequence=%s", device_id, model.sequence
                    )
                else:
                    logger.info(
                        "ignored duplicate telemetry device=%s sequence=%s",
                        device_id,
                        model.sequence,
                    )
                return inserted
            if kind == "status":
                model = DeviceStatus.model_validate(document)
                self.repository.store_status(model, received_at)
                self._emit("status", model.model_dump(mode="json"), received_at)
                logger.info("device status device=%s status=%s", device_id, model.status)
                return True
            model = ConfigAck.model_validate(document)
            self.repository.store_config_ack(model, received_at)
            self._emit("config_ack", model.model_dump(mode="json"), received_at)
            return True
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            self.repository.record_rejection(
                topic=topic,
                reason=str(exc),
                payload_size=len(payload),
                received_at=received_at,
                device_id=device_id,
            )
            logger.warning("rejected MQTT message topic=%s reason=%s", topic, exc)
            self._emit("rejected", {"topic": topic, "reason": str(exc)}, received_at)
            return False

    @staticmethod
    def _reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number is not allowed: {value}")

    def _emit(self, event_type: str, data: dict[str, Any], received_at: datetime) -> None:
        if self.event_callback:
            self.event_callback(
                {
                    "event": event_type,
                    "data": data,
                    "received_at": received_at.isoformat().replace("+00:00", "Z"),
                }
            )
