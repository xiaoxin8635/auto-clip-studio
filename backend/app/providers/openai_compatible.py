from __future__ import annotations

import json
import asyncio
import re
from pathlib import Path

import httpx
from pydantic import ValidationError, TypeAdapter

from ..schemas import ProviderResult, ProviderSegment, Transcript
from .base import AIProvider, ProviderError


class OpenAICompatibleProvider(AIProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        transcribe_model: str | None = None,
        caption_suffix: str | None = None,
        timeout: float = 120.0,
        max_attempts: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.transcribe_model = transcribe_model or model
        self.caption_suffix = caption_suffix
        self.timeout = timeout
        self.max_attempts = max_attempts

        self._transcript_adapter = TypeAdapter(Transcript)

    async def analyze(self, media_path: Path, duration_ms: int) -> ProviderResult:
        transcript = Transcript.model_validate(await self._transcribe(media_path, duration_ms))
        return ProviderResult.model_validate(
            {
                "transcript": transcript.model_dump(),
                "segments": await self.select_segments(transcript.model_dump(), duration_ms),
            }
        )

    async def _transcribe(self, media_path: Path, duration_ms: int) -> dict:
        if self.caption_suffix:
            caption_path = media_path.with_name(media_path.name + self.caption_suffix)
            if not caption_path.exists():
                raise ProviderError(f"Caption file is missing: {caption_path.name}")
            try:
                return parse_srt(caption_path.read_text(encoding="utf-8-sig"), duration_ms)
            except OSError as error:
                raise ProviderError(f"Caption file cannot be read: {error}") from error
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                with media_path.open("rb") as media:
                    response = await self._request_with_retry(
                        client,
                        "POST",
                        f"{self.base_url}/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        data={"model": self.transcribe_model, "response_format": "verbose_json"},
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
                    normalized = [{"start_ms": 0, "end_ms": max(duration_ms, 1000), "text": text[:2000]}]
                return {"language": str(payload.get("language") or "zh"), "cues": normalized}
        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, asyncio.TimeoutError) as exc:
            raise ProviderError(f"Transcription failed: {exc}") from exc

    async def select_segments(self, transcript: dict, duration_ms: int) -> list[dict]:
        if not isinstance(transcript, dict):
            raise ProviderError("Segment selection requires a transcript object")
        try:
            normalized_transcript = self._transcript_adapter.validate_python(transcript).model_dump()
        except ValidationError as error:
            raise ProviderError("Transcript failed schema validation") from error
        cues = normalized_transcript["cues"]
        if not cues:
            raise ProviderError("Transcript contains no usable cues")
        prompt = (
            "你是短视频剪辑策划。请从转录中选出 3 到 5 个适合 9:16 短视频的片段。"
            f"视频总长 {duration_ms} 毫秒。只输出 JSON，格式为 "
            '{"segments":[{"title":"...","rationale":"...","start_ms":0,"end_ms":0,"caption_text":"..."}]}。'
            "片段必须完整、不重叠、边界在视频范围内。start_ms 必须取某个 cue 的 start_ms，"
            "end_ms 必须取某个 cue 的 end_ms，不要发明任意毫秒边界。"
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
                parsed = extract_json_object(content)
                if not isinstance(parsed, dict) or not isinstance(parsed.get("segments"), list):
                    raise ProviderError("Segment selection response has no segments list")
                return snap_segments_to_cues(normalize_segments(parsed.get("segments", [])), cues, duration_ms)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ProviderError(f"Segment selection failed: {exc}") from exc

    async def _request_with_retry(self, client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code in {408, 429} or response.status_code >= 500:
                    last_error = httpx.HTTPStatusError(
                        f"Provider returned {response.status_code}", request=response.request, response=response
                    )
                    if attempt + 1 == self.max_attempts:
                        raise last_error
                else:
                    response.raise_for_status()
                    return response
            except httpx.TransportError as exc:
                last_error = exc
                if attempt + 1 == self.max_attempts:
                    raise ProviderError(f"Provider transport failed: {exc}") from exc
            await asyncio.sleep(0.5 * (2**attempt))
        raise last_error or ProviderError("Provider request failed")


def parse_srt(content: str, duration_ms: int) -> dict:
    cues = []
    for block in re.split(r"\r?\n\r?\n", content.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2 or "-->" not in lines[1]:
            continue
        match = re.match(
            r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", lines[1]
        )
        if not match:
            continue
        values = [int(value) for value in match.groups()]
        start = values[0] * 3_600_000 + values[1] * 60_000 + values[2] * 1000 + values[3]
        end = values[4] * 3_600_000 + values[5] * 60_000 + values[6] * 1000 + values[7]
        text = " ".join(lines[2:]).strip()
        if end <= start or not text:
            continue
        # Official caption feeds occasionally contain malformed trailing cues.
        if end > duration_ms:
            end = duration_ms
        if end <= start:
            continue
        cues.append({"start_ms": start, "end_ms": min(end, duration_ms), "text": text})
    if not cues:
        raise ProviderError("Caption file contains no usable cues")
    return {"language": "en", "cues": cues}


def normalize_segments(segments: list[dict]) -> list[dict]:
    normalized = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        candidate = dict(segment)
        if not str(candidate.get("rationale") or "").strip():
            candidate["rationale"] = "模型未返回选段理由；已按标题、时间和字幕内容校验。"
        normalized.append(candidate)
    return normalized


def snap_segments_to_cues(segments: list[dict], cues: list[dict], duration_ms: int) -> list[dict]:
    """Snap model boundaries to transcript cue boundaries before schema validation."""
    if duration_ms <= 0:
        raise ProviderError("Video duration must be positive")
    if not cues:
        raise ProviderError("No transcript cue boundaries are available")

    start_candidates: list[int] = []
    end_candidates: list[int] = []
    for cue in cues:
        if not isinstance(cue, dict):
            raise ProviderError("Transcript cue must be an object")
        start_ms = cue.get("start_ms")
        end_ms = cue.get("end_ms")
        if not isinstance(start_ms, int) or not isinstance(end_ms, int):
            raise ProviderError("Transcript cue boundaries must be integers")
        if start_ms < 0 or end_ms <= start_ms or end_ms > duration_ms:
            raise ProviderError("Transcript cue boundaries are outside the video")
        start_candidates.append(start_ms)
        end_candidates.append(end_ms)

    snapped_segments: list[tuple[int, int, dict]] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        raw_start = segment.get("start_ms")
        raw_end = segment.get("end_ms")
        if not isinstance(raw_start, int) or not isinstance(raw_end, int):
            continue
        start_ms = min(start_candidates, key=lambda value: (abs(value - raw_start), value))
        end_ms = min(end_candidates, key=lambda value: (abs(value - raw_end), value))
        if start_ms < 0 or end_ms <= start_ms or end_ms > duration_ms:
            continue
        if any(start_ms < accepted_end and accepted_start < end_ms for accepted_start, accepted_end, _ in snapped_segments):
            continue
        snapped_segments.append((start_ms, end_ms, segment))

    snapped_segments.sort(key=lambda item: (item[0], item[1]))
    if not snapped_segments:
        raise ProviderError("No model segments remain after transcript boundary snapping")

    result = []
    for start_ms, end_ms, segment in snapped_segments:
        candidate = dict(segment)
        candidate["start_ms"] = start_ms
        candidate["end_ms"] = end_ms
        try:
            result.append(ProviderSegment.model_validate(candidate).model_dump())
        except ValidationError as error:
            raise ProviderError("Segment selection output failed schema validation") from error
    return result


def extract_json_object(content: str) -> dict | list | None:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            return None
