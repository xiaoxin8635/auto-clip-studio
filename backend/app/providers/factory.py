from __future__ import annotations

from ..config import Settings
from .base import AIProvider, ProviderError
from .mock import MockProvider
from .openai_compatible import OpenAICompatibleProvider
from .qwen_asr import QwenAsrConfig, QwenAsrSelectorProvider
from .oss_uploader import OssSignerUploader


def create_provider(settings: Settings) -> AIProvider:
    if settings.provider == "mock":
        return MockProvider()
    if settings.provider == "openai-compatible":
        missing = [
            name
            for name, value in {
                "AUTOCLIP_AI_BASE_URL": settings.ai_base_url,
                "AUTOCLIP_AI_API_KEY": settings.ai_api_key,
                "AUTOCLIP_AI_MODEL": settings.ai_model,
            }.items()
            if not value
        ]
        if missing:
            raise ProviderError(f"Missing provider settings: {', '.join(missing)}")
        return OpenAICompatibleProvider(
            settings.ai_base_url,
            settings.ai_api_key,
            settings.ai_model,
            transcribe_model=settings.transcribe_model,
            caption_suffix=settings.caption_suffix,
        )
    if settings.provider == "qwen-asr-openai-compatible":
        missing = [
            name
            for name, value in {
                "AUTOCLIP_AI_API_KEY": settings.ai_api_key,
                "AUTOCLIP_AI_MODEL": settings.ai_model,
                "AUTOCLIP_QWEN_ASR_MODEL": settings.qwen_asr_model,
                "AUTOCLIP_OSS_BUCKET": settings.oss_bucket,
                "AUTOCLIP_OSS_ENDPOINT": settings.oss_endpoint,
                "AUTOCLIP_OSS_ACCESS_KEY_ID": settings.oss_access_key_id,
                "AUTOCLIP_OSS_ACCESS_KEY_SECRET": settings.oss_access_key_secret,
            }.items()
            if not value
        ]
        if missing:
            raise ProviderError(f"Missing provider settings: {', '.join(missing)}")
        selector = OpenAICompatibleProvider(
            settings.ai_base_url or "https://peuyai.ulib.top/v1",
            settings.ai_api_key,
            settings.ai_model,
        )
        uploader = OssSignerUploader(
            settings.oss_bucket or "",
            settings.oss_endpoint or "",
            settings.oss_access_key_id or "",
            settings.oss_access_key_secret or "",
        )
        return QwenAsrSelectorProvider(
            QwenAsrConfig(settings.asr_api_key or "", settings.qwen_asr_model or "", uploader),
            selector,
        )
    raise ProviderError(f"Unknown provider: {settings.provider}")
