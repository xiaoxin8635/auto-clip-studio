import asyncio
from pathlib import Path

import httpx
import pytest
import respx

from app.providers.base import ProviderError
from app.providers.qwen_asr import (
    QwenAsrConfig,
    normalize_transcription,
    transcribe_with_qwen,
)


class FakeUploader:
    def upload(self, source: Path, destination_name: str) -> str:
        return "https://storage.test/audio.mp4"


def fake_extract_audio(source: Path) -> Path:
    return source.with_name(f"{source.stem}.m4a")


def config() -> QwenAsrConfig:
    return QwenAsrConfig(api_key="key", model="paraformer-v2", uploader=FakeUploader())


@respx.mock
async def test_transcribe_with_qwen_polls_and_normalizes_result(tmp_path: Path):
    respx.post("https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription").mock(
        return_value=httpx.Response(200, json={"output": {"task_id": "task-1"}})
    )
    running = respx.get("https://dashscope.aliyuncs.com/api/v1/tasks/task-1").mock(
        return_value=httpx.Response(200, json={"output": {"task_status": "RUNNING"}})
    )
    succeeded = respx.get("https://dashscope.aliyuncs.com/api/v1/tasks/task-1").mock(
        return_value=httpx.Response(
            200,
            json={"output": {"task_status": "SUCCEEDED", "results": [{"transcription_url": "https://result.test"}]}},
        )
    )
    respx.get("https://result.test").mock(
        return_value=httpx.Response(
            200,
            json={
                "language": "en",
                "transcripts": [
                    {
                        "sentences": [
                            {"begin_time": 1200, "end_time": 3400, "text": "Hello"},
                            {"begin_time": 3500, "end_time": 20000, "text": "World"},
                        ]
                    }
                ],
            },
        )
    )

    result = await transcribe_with_qwen(
        tmp_path / "video.mp4",
        5000,
        config(),
        extract_audio_callable=fake_extract_audio,
        poll_interval_seconds=0,
    )

    assert running.call_count == 1
    assert succeeded.called
    assert result == {
        "language": "en",
        "cues": [
            {"start_ms": 1200, "end_ms": 3400, "text": "Hello"},
            {"start_ms": 3500, "end_ms": 5000, "text": "World"},
        ],
    }


@respx.mock
async def test_transcribe_with_qwen_reports_task_failure(tmp_path: Path):
    respx.post("https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription").mock(
        return_value=httpx.Response(200, json={"output": {"task_id": "task-2"}})
    )
    respx.get("https://dashscope.aliyuncs.com/api/v1/tasks/task-2").mock(
        return_value=httpx.Response(200, json={"output": {"task_status": "FAILED", "message": "bad audio"}})
    )

    with pytest.raises(ProviderError, match="bad audio"):
        await transcribe_with_qwen(
            tmp_path / "video.mp4",
            5000,
        config(),
        extract_audio_callable=fake_extract_audio,
            poll_interval_seconds=0,
        )


def test_normalize_transcription_rejects_missing_cues():
    with pytest.raises(ProviderError, match="no timestamped cues"):
        normalize_transcription({"transcripts": [{"sentences": []}]}, 1000)
