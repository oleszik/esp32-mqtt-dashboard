import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .models import validate_device_id
from .mqtt_consumer import MqttConsumer
from .repository import Repository
from .services import MessageProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"


class EventHub:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind(self) -> None:
        self._loop = asyncio.get_running_loop()

    def publish_threadsafe(self, event: dict[str, Any]) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(self._publish, event)

    def _publish(self, event: dict[str, Any]) -> None:
        for subscriber in list(self._subscribers):
            if subscriber.full():
                with suppress(asyncio.QueueEmpty):
                    subscriber.get_nowait()
            subscriber.put_nowait(event)

    async def subscribe(self) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        try:
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:  # noqa: UP041 - Python 3.10-compatible local checks.
                    yield {"event": "keepalive", "data": {}}
        finally:
            self._subscribers.discard(queue)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    repository = Repository(config.database_path)
    hub = EventHub()
    processor = MessageProcessor(repository, config.max_payload_bytes, hub.publish_threadsafe)
    consumer = MqttConsumer(config, processor) if config.mqtt_enabled else None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        hub.bind()
        if consumer:
            consumer.start()
        logger.info("backend started database=%s", config.database_path)
        yield
        if consumer:
            consumer.stop()
        repository.close()
        logger.info("backend stopped")

    app = FastAPI(title="ESP32 MQTT Dashboard", version="1.0.0", lifespan=lifespan)
    app.state.settings = config
    app.state.repository = repository
    app.state.processor = processor
    app.state.consumer = consumer
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        mqtt_connected = consumer.connected if consumer else None
        return {
            "status": "healthy" if repository.ping() else "unhealthy",
            "database": "connected",
            "mqtt": "connected" if mqtt_connected else "disconnected",
        }

    @app.get("/api/devices")
    async def devices() -> list[dict[str, Any]]:
        return repository.list_devices(config.stale_after_seconds)

    @app.get("/api/devices/{device_id}")
    async def device(device_id: str) -> dict[str, Any]:
        try:
            validate_device_id(device_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        result = repository.get_device(device_id, config.stale_after_seconds)
        if result is None:
            raise HTTPException(status_code=404, detail="device not found")
        return result

    @app.get("/api/devices/{device_id}/telemetry")
    async def telemetry(
        device_id: str, limit: int = Query(default=100, ge=1, le=1000)
    ) -> list[dict[str, Any]]:
        try:
            validate_device_id(device_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return repository.telemetry_history(device_id, limit)

    @app.get("/api/events")
    async def events(limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, Any]]:
        return repository.recent_events(limit)

    @app.get("/api/stream")
    async def stream(request: Request) -> StreamingResponse:
        async def generate() -> AsyncIterator[str]:
            async for event in hub.subscribe():
                if await request.is_disconnected():
                    break
                event_name = event["event"]
                data = json.dumps(event, separators=(",", ":"), default=str)
                yield f"event: {event_name}\ndata: {data}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()
