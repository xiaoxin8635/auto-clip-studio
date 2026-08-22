from __future__ import annotations

import json
from pathlib import Path

import httpx

from ..schemas import ProviderResult, Transcript
from .base import AIProvider, ProviderError


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def analyze(self, media_path: Path, duration_ms: int) -> ProviderResult:
        transcript = Transcript.model_validate(await self._transcribe(media_path))
        return ProviderResult.model_validate(
            {
                "transcript": transcript.model_dump(),
                "segments": await self._select_segments(transcript.model_dump(), duration_ms),
            }
        )

    async def _transcribe(self, media_path: Path) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                with media_path.open("rb") as media:
                    response = await client.post(
                        f"{self.base_url}/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        data={"model": self.model, "response_format": "verbose_json"},
                        files={"file": (media_path.name, media, "application/octet-stream")},
                    )
                response.raise_for_status()
                payload = response.json()
                cues = payload.get("segments") or []
                normalized = [
                    {
                        "start_ms": int(float(item["start"]) * 1000),
                        "end_ms": int(float(item["end"]) * 1000),
                        "text": str(item.get("text", "")).strip(),
                    }
                    for item in cues
                    if item.get("start") is not None and item.get("end") is not None and str(item.get("text", "")).strip()
                ]
                if not normalized:
                    text = str(payload.get("text", "")).strip()
                    if not text:
                        raise ProviderError("Transcription provider returned no text")
                    normalized = [{"start_ms": 0, "end_ms": min(duration_ms, 5000), "text": text[:2000]}]
                return {"language": str(payload.get("language") or "zh"), "cues": normalized}
        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ProviderError(f"Transcription failed: {exc}") from exc

    async def _select_segments(self, transcript: dict, duration_ms: int) -> list[dict]:
        prompt = (
            "你是短视频剪辑策划。请从转录中选出 3 到 5 个适合 9:16 短视频的片段。"
            f"视频总长 {duration_ms} 毫秒。只输出 JSON，格式为 "
            '{"segments":[{"title":"...","rationale":"...","start_ms":0,"end_ms":0,"caption_text":"..."}]}。'
            "片段必须完整、不重叠、边界在视频范围内。"
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": json.dumps(transcript, ensure_ascii=False)},
                        ],
                        "temperature": 0.2,
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                parsed = json.loads(content[content.find("{") : content.rfind("}") + 1])
                return parsed.get("segments", [])
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ProviderError(f"Segment selection failed: {exc}") from exc
