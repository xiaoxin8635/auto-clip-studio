from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from ..schemas import ProviderResult, Transcript, TranscriptCue
from .base import AIProvider, ProviderError
from .openai_compatible import OpenAICompatibleProvider


class AudioUrlUploader(Protocol):
    def upload(self, source: Path, destination_name: str) -> str:
        """Upload media and return a URL accessible to the ASR service."""


@dataclass(frozen=True)
class QwenAsrConfig:
    api_key: str
    model: str
    uploader: AudioUrlUploader
    base_url: str = "https://dashscope.aliyuncs.com"


class QwenAsrSelectorProvider(AIProvider):
    """Transcribe with DashScope Qwen ASR, then select segments with an LLM."""

    def __init__(
        self,
        asr_config: QwenAsrConfig,
        selector: OpenAICompatibleProvider,
        poll_interval_seconds: float = 2.0,
        timeout_seconds: int = 900,
    ):
        self.asr_config = asr_config
        self.selector = selector
        self.poll_interval_seconds = poll_interval_seconds
        self.timeout_seconds = timeout_seconds

    async def analyze(self, media_path: Path, duration_ms: int) -> ProviderResult:
        transcript_payload = await transcribe_with_qwen(
            media_path,
            duration_ms,
            self.asr_config,
            poll_interval_seconds=self.poll_interval_seconds,
            timeout_seconds=self.timeout_seconds,
        )
        transcript = Transcript.model_validate(transcript_payload)
        segments = await self.selector.select_segments(transcript.model_dump(), duration_ms)
        return ProviderResult.model_validate({"transcript": transcript.model_dump(), "segments": segments})


async def transcribe_with_qwen(
    media_path: Path,
    duration_ms: int,
    config: QwenAsrConfig,
    client: httpx.AsyncClient | None = None,
    poll_interval_seconds: float = 2.0,
    timeout_seconds: int = 900,
) -> dict:
    try:
        audio_url = await asyncio.to_thread(config.uploader.upload, media_path, media_path.name)
    except (OSError, RuntimeError) as error:
        raise ProviderError(f"Audio upload failed: {error}") from error

    own_client = client is None
    client = client or httpx.AsyncClient(timeout=60)
    headers = {"Authorization": f"Bearer {config.api_key}"}
    submit_payload = {
        "model": config.model,
        "input": {"file_url": audio_url},
        "parameters": {"timestamp": True},
    }
    try:
        submission = await client.post(
            f"{config.base_url}/api/v1/services/audio/asr/transcription",
            headers=headers,
            json=submit_payload,
        )
        submission.raise_for_status()
        task_id = submission.json().get("output", {}).get("task_id")
        if not task_id:
            raise ProviderError("Qwen ASR submission returned no task id")

        result = await wait_for_task(client, config.base_url, headers, task_id, poll_interval_seconds, timeout_seconds)
        transcription_url = extract_transcription_url(result)
        transcription = await client.get(transcription_url)
        transcription.raise_for_status()
        return normalize_transcription(transcription.json(), duration_ms)
    except ProviderError:
        raise
    except (httpx.HTTPError, ValueError, KeyError, TypeError, asyncio.TimeoutError) as error:
        raise ProviderError(f"Qwen ASR failed: {error}") from error
    finally:
        if own_client:
            await client.aclose()


async def wait_for_task(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    task_id: str,
    poll_interval_seconds: float,
    timeout_seconds: int,
) -> dict:
    async with asyncio.timeout(timeout_seconds):
        while True:
            response = await client.get(
                f"{base_url}/api/v1/tasks/{task_id}",
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
            status = payload.get("output", {}).get("task_status")
            if status == "SUCCEEDED":
                return payload
            if status in {"FAILED", "CANCELED"}:
                message = payload.get("output", {}).get("message", "Qwen ASR task failed")
                raise ProviderError(f"Qwen ASR failed: {message}")
            await asyncio.sleep(poll_interval_seconds)


def extract_transcription_url(payload: dict) -> str:
    try:
        return payload["output"]["results"][0]["transcription_url"]
    except (KeyError, IndexError, TypeError) as error:
        raise ProviderError("Qwen ASR result has no transcription_url") from error


def normalize_transcription(payload: dict, duration_ms: int) -> dict:
    language = str(payload.get("language") or payload.get("language_hint") or "zh")[:8]
    cues = []
    for sentence in payload.get("transcripts", []):
        for cue in sentence.get("sentences", []):
            start = cue.get("begin_time")
            end = cue.get("end_time")
            text = str(cue.get("text", "")).strip()
            if start is None or end is None or not text:
                continue
            start_ms = int(float(start) * 1000)
            end_ms = int(float(end) * 1000)
            if end_ms <= start_ms:
                continue
            cues.append(
                {
                    "start_ms": start_ms,
                    "end_ms": min(end_ms, duration_ms),
                    "text": text[:2000],
                }
            )
    if not cues:
        raise ProviderError("Qwen ASR returned no timestamped cues")
    return {"language": language, "cues": cues}
