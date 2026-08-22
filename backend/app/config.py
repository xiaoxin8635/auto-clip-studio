from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    data_dir: Path = Path(".local")
    provider: str = "mock"
    ai_base_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = None
    max_upload_bytes: int = 500 * 1024 * 1024
    environment: str = "local"


@lru_cache
def get_settings() -> Settings:
    import os

    return Settings(
        data_dir=Path(os.getenv("AUTOCLIP_DATA_DIR", ".local")).resolve(),
        provider=os.getenv("AUTOCLIP_PROVIDER", "mock").lower(),
        ai_base_url=os.getenv("AUTOCLIP_AI_BASE_URL"),
        ai_api_key=os.getenv("AUTOCLIP_AI_API_KEY"),
        ai_model=os.getenv("AUTOCLIP_AI_MODEL"),
        environment=os.getenv("AUTOCLIP_ENV", "local"),
    )
