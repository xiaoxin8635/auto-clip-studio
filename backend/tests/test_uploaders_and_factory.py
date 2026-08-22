from pathlib import Path

import pytest
import respx
import httpx

from app.config import Settings
from app.providers.base import ProviderError
from app.providers.factory import create_provider
from app.providers.qwen_asr import QwenAsrSelectorProvider
from app.providers.uploaders import HttpPutUploader


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
        qwen_asr_model="qwen-audio-asr",
        media_upload_url_template="https://storage.test/{name}?sig=test",
    )

    provider = create_provider(settings)

    assert isinstance(provider, QwenAsrSelectorProvider)


def test_http_put_uploader_rejects_template_without_name():
    with pytest.raises(ValueError, match="must contain"):
        HttpPutUploader("https://storage.test")


@respx.mock
def test_http_put_uploader_uploads_file_and_returns_url(tmp_path: Path):
    media = tmp_path / "video.mp4"
    media.write_bytes(b"media")
    route = respx.put("https://storage.test/video.mp4").mock(return_value=httpx.Response(200))
    uploader = HttpPutUploader("https://storage.test/{name}")

    assert uploader.upload(media, media.name) == "https://storage.test/video.mp4"
    assert route.called
