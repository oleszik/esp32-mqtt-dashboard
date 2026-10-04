import logging
import queue
import threading
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt

from .config import Settings
from .services import MessageProcessor

logger = logging.getLogger(__name__)


class MqttConsumer:
    def __init__(
        self,
        settings: Settings,
        processor: MessageProcessor,
        connection_callback: Callable[[bool], None] | None = None,
    ) -> None:
        self.settings = settings
        self.processor = processor
        self.connection_callback = connection_callback
        self._messages: queue.Queue[tuple[str, bytes] | None] = queue.Queue(maxsize=1000)
        self._worker = threading.Thread(target=self._work, name="mqtt-db-worker", daemon=True)
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.mqtt_client_id,
        )
        self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self.connected = False

    def start(self) -> None:
        self._worker.start()
        self._client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=30)
        self._client.loop_start()
        logger.info(
            "MQTT consumer starting host=%s port=%s",
            self.settings.mqtt_host,
            self.settings.mqtt_port,
        )

    def stop(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()
        self._messages.put(None)
        self._worker.join(timeout=5)

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
            logger.error("MQTT connection failed reason=%s", reason_code)
            return
        for topic in (
            "iot/v1/devices/+/telemetry",
            "iot/v1/devices/+/status",
            "iot/v1/devices/+/config/ack",
        ):
            client.subscribe(topic, qos=1)
        self.connected = True
        if self.connection_callback:
            self.connection_callback(True)
        logger.info("MQTT connected and subscriptions active")

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        del client, userdata, disconnect_flags, properties
        self.connected = False
        if self.connection_callback:
            self.connection_callback(False)
        logger.warning("MQTT disconnected reason=%s", reason_code)

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        del client, userdata
        try:
            self._messages.put_nowait((message.topic, bytes(message.payload)))
        except queue.Full:
            logger.error("MQTT processing queue full; dropping topic=%s", message.topic)

    def _work(self) -> None:
        while True:
            item = self._messages.get()
            try:
                if item is None:
                    return
                self.processor.process(*item)
            except Exception:
                logger.exception("unexpected message worker error")
            finally:
                self._messages.task_done()
