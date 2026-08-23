from app.providers.mock import MockProvider
from app.providers.base import ProviderError
from app.providers.openai_compatible import (
    OpenAICompatibleProvider,
    extract_json_object,
    normalize_segments,
    parse_srt,
    snap_segments_to_cues,
)
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


def test_normalize_segments_defaults_missing_rationale():
    segments = normalize_segments([{"title": "Valid", "start_ms": 1, "end_ms": 2, "rationale": ""}])

    assert segments[0]["rationale"]


def test_snap_segments_uses_exact_cue_boundaries():
    cues = [
        {"start_ms": 1000, "end_ms": 3000, "text": "first"},
        {"start_ms": 3000, "end_ms": 6000, "text": "second"},
    ]
    segment = {"title": "Exact", "rationale": "Exact cue", "start_ms": 1000, "end_ms": 6000}

    snapped = snap_segments_to_cues([segment], cues, 6000)

    assert snapped == [{**segment, "caption_text": ""}]


def test_snap_segments_prefers_nearest_cue_boundary():
    cues = [
        {"start_ms": 0, "end_ms": 2000, "text": "first"},
        {"start_ms": 2000, "end_ms": 5000, "text": "second"},
        {"start_ms": 5000, "end_ms": 9000, "text": "third"},
    ]
    segment = {"title": "Middle", "rationale": "Nearest boundaries", "start_ms": 1900, "end_ms": 8200}

    snapped = snap_segments_to_cues([segment], cues, 9000)

    assert snapped[0]["start_ms"] == 2000
    assert snapped[0]["end_ms"] == 9000


def test_snap_segments_rejects_reversed_boundary():
    cues = [{"start_ms": 0, "end_ms": 2000, "text": "first"}, {"start_ms": 2000, "end_ms": 4000, "text": "second"}]
    segment = {"title": "Reversed", "rationale": "Snaps backwards", "start_ms": 1900, "end_ms": 100}

    with pytest.raises(ProviderError, match="No model segments remain"):
        snap_segments_to_cues([segment], cues, 4000)


def test_snap_segments_rejects_cue_beyond_duration():
    cues = [{"start_ms": 0, "end_ms": 2000, "text": "first"}, {"start_ms": 2000, "end_ms": 4500, "text": "second"}]
    segment = {"title": "Too late", "rationale": "Beyond video", "start_ms": 2000, "end_ms": 4000}

    with pytest.raises(ProviderError, match="outside the video"):
        snap_segments_to_cues([segment], cues, 4000)


def test_snap_segments_drops_overlap_after_snapping():
    cues = [
        {"start_ms": 0, "end_ms": 2000, "text": "first"},
        {"start_ms": 2000, "end_ms": 5000, "text": "second"},
        {"start_ms": 5000, "end_ms": 8000, "text": "third"},
    ]
    segments = [
        {"title": "Second", "rationale": "Original second", "start_ms": 2100, "end_ms": 5100},
        {"title": "Later", "rationale": "Overlaps after snap", "start_ms": 2100, "end_ms": 7900},
    ]

    snapped = snap_segments_to_cues(segments, cues, 8000)

    assert [(item["start_ms"], item["end_ms"]) for item in snapped] == [(2000, 5000)]


def test_snap_segments_requires_cues():
    segment = {"title": "No cues", "rationale": "No boundaries", "start_ms": 0, "end_ms": 1000}

    with pytest.raises(ProviderError, match="No transcript cue boundaries"):
        snap_segments_to_cues([segment], [], 1000)


def test_snap_segments_preserves_schema_validation():
    cues = [{"start_ms": 0, "end_ms": 1500, "text": "only"}]
    segments = [
        {"title": "", "rationale": "Invalid title", "start_ms": 0, "end_ms": 1500},
    ]

    with pytest.raises(ProviderError, match="schema validation"):
        snap_segments_to_cues(segments, cues, 1500)


def test_parse_srt_discards_malformed_trailing_cue():
    content = (
        "1\n00:00:00,000 --> 00:00:01,000\nvalid\n\n"
        "2\n00:00:02,000 --> 00:00:03,000\nmalformed\n"
    )

    cues = parse_srt(content, 1500)["cues"]

    assert [cue["start_ms"] for cue in cues] == [0]


@respx.mock
async def test_select_segments_rejects_missing_cues():
    provider = OpenAICompatibleProvider("https://provider.test/v1", "key", "model", timeout=1)

    with pytest.raises(ProviderError, match="no usable cues"):
        await provider.select_segments({"language": "en", "cues": []}, 1_000)


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
