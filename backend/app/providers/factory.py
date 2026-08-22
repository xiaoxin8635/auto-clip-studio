from __future__ import annotations

from ..config import Settings
from .base import AIProvider, ProviderError
from .mock import MockProvider
from .openai_compatible import OpenAICompatibleProvider
from .qwen_asr import QwenAsrConfig, QwenAsrSelectorProvider
from .uploaders import HttpPutUploader


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
                "AUTOCLIP_MEDIA_UPLOAD_URL_TEMPLATE": settings.media_upload_url_template,
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
        uploader = HttpPutUploader(settings.media_upload_url_template or "")
        return QwenAsrSelectorProvider(
            QwenAsrConfig(settings.ai_api_key, settings.qwen_asr_model or "", uploader),
            selector,
        )
    raise ProviderError(f"Unknown provider: {settings.provider}")
