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
    asr_api_key: str | None = None
    transcribe_model: str | None = None
    caption_suffix: str | None = None
    qwen_asr_model: str | None = None
    oss_bucket: str | None = None
    oss_endpoint: str | None = None
    oss_access_key_id: str | None = None
    oss_access_key_secret: str | None = None
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
        asr_api_key=os.getenv("AUTOCLIP_ASR_API_KEY"),
        transcribe_model=os.getenv("AUTOCLIP_TRANSCRIBE_MODEL"),
        caption_suffix=os.getenv("AUTOCLIP_CAPTION_SUFFIX"),
        qwen_asr_model=os.getenv("AUTOCLIP_QWEN_ASR_MODEL"),
        oss_bucket=os.getenv("AUTOCLIP_OSS_BUCKET"),
        oss_endpoint=os.getenv("AUTOCLIP_OSS_ENDPOINT"),
        oss_access_key_id=os.getenv("AUTOCLIP_OSS_ACCESS_KEY_ID"),
        oss_access_key_secret=os.getenv("AUTOCLIP_OSS_ACCESS_KEY_SECRET"),
        environment=os.getenv("AUTOCLIP_ENV", "local"),
    )
