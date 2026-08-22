from app.providers.mock import MockProvider
from app.providers.openai_compatible import OpenAICompatibleProvider, extract_json_object
from app.schemas import ProviderResult
import json
import pytest
import respx
import httpx


def test_mock_provider_result_is_valid_and_bounded(tmp_path):
    import asyncio

    result = asyncio.run(MockProvider().analyze(tmp_path / "input.mp4", 180_000))
    assert isinstance(result, ProviderResult)
    assert len(result.segments) == 3
    assert all(segment.end_ms <= 180_000 for segment in result.segments)


def test_extract_json_object_handles_wrapped_output():
    assert extract_json_object('```json\n{"segments": []}\n```') == {"segments": []}
    assert extract_json_object("not json") is None


@respx.mock
async def test_provider_uses_local_captions_for_transcript(tmp_path):
    provider = OpenAICompatibleProvider(
        "https://provider.test/v1",
        "key",
        "glm-5.3",
        caption_suffix=".srt",
        timeout=1,
    )
    media_path = tmp_path / "video.mp4"
    media_path.write_bytes(b"fake mp4")
    media_path.with_suffix(".mp4.srt").write_text(
        "1\n00:00:01,000 --> 00:00:03,000\nHello from captions\n",
        encoding="utf-8",
    )
    route = respx.post("https://provider.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "segments": [
                                        {
                                            "title": "Caption segment",
                                            "rationale": "Complete point",
                                            "start_ms": 1000,
                                            "end_ms": 3000,
                                            "caption_text": "Hello from captions",
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ]
            },
        )
    )
    result = await provider.analyze(media_path, 5_000)
    assert route.called
    assert result.transcript.cues[0].text == "Hello from captions"
    assert result.segments[0].caption_text == "Hello from captions"


@respx.mock
async def test_provider_retries_rate_limit(tmp_path):
    provider = OpenAICompatibleProvider("https://provider.test/v1", "key", "model", timeout=1, max_attempts=2)
    media_path = tmp_path / "video.mp4"
    media_path.write_bytes(b"fake mp4")
    route = respx.post("https://provider.test/v1/audio/transcriptions").mock(
        side_effect=[
            httpx.Response(429, json={"error": "rate limit"}),
            httpx.Response(
                200,
                json={"text": "hello", "language": "en", "segments": [{"start": 0, "end": 2, "text": "hello"}]},
            ),
        ]
    )
    respx.post("https://provider.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "segments": [
                                        {
                                            "title": "Hello",
                                            "rationale": "Opening",
                                            "start_ms": 0,
                                            "end_ms": 2000,
                                            "caption_text": "hello",
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ]
            },
        )
    )
    result = await provider.analyze(media_path, 10_000)
    assert route.call_count == 2
    assert result.transcript.cues[0].text == "hello"
