from __future__ import annotations

from ..config import Settings
from .base import AIProvider, ProviderError
from .mock import MockProvider
from .openai_compatible import OpenAICompatibleProvider


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
        return OpenAICompatibleProvider(settings.ai_base_url, settings.ai_api_key, settings.ai_model)
    raise ProviderError(f"Unknown provider: {settings.provider}")
