import json
from pathlib import Path

import pytest

from app.evaluation_runner import EvaluationOutputItem, _load_annotations, main
from app.providers.base import ProviderError
from app.schemas import ProviderResult, ProviderSegment, Transcript, TranscriptCue


class DeterministicProvider:
    async def analyze(self, media_path: Path, duration_ms: int) -> ProviderResult:
        return ProviderResult(
            transcript=Transcript(cues=[TranscriptCue(start_ms=0, end_ms=duration_ms, text="hello")]),
            segments=[
                ProviderSegment(
                    title="Hello",
                    rationale="Opening",
                    start_ms=0,
                    end_ms=1000,
                )
            ],
        )


class FailingProvider:
    async def analyze(self, media_path: Path, duration_ms: int) -> ProviderResult:
        raise ProviderError("selector unavailable")


def test_load_annotations_rejects_invalid_file(tmp_path: Path) -> None:
    path = tmp_path / "annotations.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="at least 1 item"):
        _load_annotations(path)


def test_runner_preserves_provider_failure_reason(tmp_path: Path) -> None:
    item = EvaluationOutputItem(video="missing.mp4", failure_reason="source video is missing")

    assert item.transcript_usable is False
    assert item.rendered is False
