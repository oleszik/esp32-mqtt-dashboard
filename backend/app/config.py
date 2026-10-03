from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mqtt_host: str = "broker"
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    mqtt_username: str = "backend"
    mqtt_password: str = "change-backend-password"
    mqtt_client_id: str = "telemetry-backend"
    database_path: Path = Path("/data/telemetry.db")
    stale_after_seconds: int = Field(default=15, ge=2, le=86400)
    max_payload_bytes: int = Field(default=4096, ge=256, le=65536)
    mqtt_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
