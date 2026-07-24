from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    public_base_url: str = "http://localhost:5173"

    redis_url: str = "redis://localhost:6379/0"
    session_ttl_seconds: int = 86400

    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 60

    giffgaff_id_base: str = "https://id.giffgaff.com"
    giffgaff_public_api_base: str = "https://publicapi.giffgaff.com"
    giffgaff_web_base: str = "https://www.giffgaff.com"

    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
