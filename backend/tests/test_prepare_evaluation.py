from pathlib import Path

import pytest

from app.prepare_evaluation import (
    MediaFile,
    PreparationError,
    choose_media,
    make_draft,
    normalize_asset_url,
    parse_srt,
    parse_srt_timestamps,
    safe_filename,
)


def test_normalize_asset_url_encodes_spaces_and_upgrades_http() -> None:
    assert (
        normalize_asset_url("http://example.com/a b/file~mobile.mp4")
        == "https://example.com/a%20b/file~mobile.mp4"
    )


def test_choose_media_prefers_highest_allowed_variant() -> None:
    files = [
        MediaFile(url="preview.mp4", variant="preview"),
        MediaFile(url="medium.mp4", variant="medium"),
        MediaFile(url="mobile.mp4", variant="mobile"),
    ]

    assert choose_media(files, "mobile").url == "mobile.mp4"
    assert choose_media(files, "medium").url == "medium.mp4"


def test_choose_media_rejects_empty_and_unknown_variant() -> None:
    with pytest.raises(PreparationError):
        choose_media([], "mobile")
    with pytest.raises(PreparationError):
        choose_media([MediaFile(url="orig.mp4", variant="orig")], "mobile")


def test_safe_filename_replaces_unsafe_characters() -> None:
    assert safe_filename('NASA: What\'s "Next"?') == "NASA-What's-Next.mp4"


def test_parse_srt_and_timestamps() -> None:
    content = "1\n00:00:01,000 --> 00:00:03,500\nHello world\n\n2\n00:00:04,000 --> 00:00:06,000\nSecond cue\n"

    assert parse_srt(content) == [(1000, 3500, "Hello world"), (4000, 6000, "Second cue")]
    assert parse_srt_timestamps("00:01:02.250 --> 00:01:04.500") == (62250, 64500)


def test_make_draft_creates_bounded_caption_segments() -> None:
    cues = [(index * 5000, index * 5000 + 4500, f"cue {index}") for index in range(12)]

    segments = make_draft(cues, duration_ms=60_000, segment_count=2)

    assert 1 <= len(segments) <= 2
    assert all(segment.start_ms < segment.end_ms <= 60_000 for segment in segments)


def test_make_draft_rejects_empty_and_short_media() -> None:
    with pytest.raises(PreparationError):
        make_draft([], 60_000, 5)
    with pytest.raises(PreparationError):
        make_draft([(0, 1000, "tiny")], 60_000, 5)
