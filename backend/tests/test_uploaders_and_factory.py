from pathlib import Path

import pytest
from app.config import Settings
from app.providers.base import ProviderError
from app.providers.factory import create_provider
from app.providers.qwen_asr import QwenAsrSelectorProvider


def test_factory_rejects_incomplete_qwen_configuration():
    settings = Settings(provider="qwen-asr-openai-compatible")

    with pytest.raises(ProviderError, match="AUTOCLIP_QWEN_ASR_MODEL"):
        create_provider(settings)


def test_factory_creates_qwen_composite_provider(tmp_path: Path):
    settings = Settings(
        provider="qwen-asr-openai-compatible",
        data_dir=tmp_path,
        ai_api_key="key",
        ai_model="glm-5.3",
        asr_api_key="asr-key",
        qwen_asr_model="paraformer-v2",
        oss_bucket="bucket",
        oss_endpoint="https://oss-cn-beijing.aliyuncs.com",
        oss_access_key_id="id",
        oss_access_key_secret="secret",
    )

    provider = create_provider(settings)

    assert isinstance(provider, QwenAsrSelectorProvider)
