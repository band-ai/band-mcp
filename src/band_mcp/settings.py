"""Environment-backed settings for band-mcp transports and API clients."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "settings"]


class Settings(BaseSettings):
    """Process-wide settings resolved from the environment and ``.env``."""

    band_api_key: str = ""
    band_base_url: str = "https://app.band.ai"
    transport: Literal["stdio", "sse"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    enable_dns_rebinding_protection: bool = True
    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_origins: list[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
