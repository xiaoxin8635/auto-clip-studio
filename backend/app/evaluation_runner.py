from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from .evaluation import Annotation
from .providers.base import AIProvider, ProviderError
from .rendering import render_segment


class EvaluatedCandidate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)


class EvaluationOutputItem(BaseModel):
    video: str = Field(min_length=1, max_length=255)
    candidates: list[EvaluatedCandidate] = Field(default_factory=list)
    transcript_usable: bool = False
    rendered: bool = False
    analysis_ms: int = Field(default=0)
    failure_reason: str = Field(default="", max_length=1000)


class EvaluationSegmentStub:
    """Minimal rendering interface shared with render_segment."""

    def __init__(self, candidate: EvaluatedCandidate):
        self.title = candidate.title
        self.start_ms = candidate.start_ms
        self.end_ms = candidate.end_ms
        self.caption_text = ""


def _write_json(path: Path, payload: list[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _load_annotations(path: Path) -> list[Annotation]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("annotations must be a JSON array")
        if not raw:
            raise ValueError("annotations must contain at least 1 item")
        return [Annotation.model_validate(item) for item in raw]
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ValueError(f"Cannot load annotations from {path}: {error}") from error


async def run_evaluation(
    annotations: list[Annotation],
    provider: AIProvider,
    video_dir: Path,
    render_dir: Path,
) -> list[EvaluationOutputItem]:
    results: list[EvaluationOutputItem] = []
    for annotation in annotations:
        source = video_dir / annotation.video
        started_at = time.monotonic()
        if not source.is_file():
            results.append(
                EvaluationOutputItem(video=annotation.video, failure_reason="source video is missing")
            )
            continue
        try:
            render_dir.mkdir(parents=True, exist_ok=True)
            analysis = await provider.analyze(source, annotation.duration_ms)
            candidates = [
                EvaluatedCandidate(title=segment.title, start_ms=segment.start_ms, end_ms=segment.end_ms)
                for segment in analysis.segments
            ]
            output = render_dir / f"{source.stem}-candidate-0.mp4"
            render_segment(source, output, EvaluationSegmentStub(candidates[0]))
            results.append(
                EvaluationOutputItem(
                    video=annotation.video,
                    candidates=candidates,
                    transcript_usable=True,
                    rendered=output.is_file() and output.stat().st_size > 0,
                    analysis_ms=int((time.monotonic() - started_at) * 1000),
                )
            )
        except (ProviderError, OSError, RuntimeError, ValueError, ValidationError, IndexError) as error:
            results.append(
                EvaluationOutputItem(
                    video=annotation.video,
                    failure_reason=str(error)[:1000],
                    analysis_ms=int((time.monotonic() - started_at) * 1000),
                )
            )
    return results


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run AutoClip Studio provider evaluation")
    parser.add_argument("annotations", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--video-dir", type=Path, required=True)
    parser.add_argument("--render-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    from .providers.factory import create_provider
    from .config import get_settings

    args = _build_parser().parse_args(argv)
    try:
        annotations = _load_annotations(args.annotations)
        items = asyncio.run(
            run_evaluation(
                annotations,
                create_provider(get_settings()),
                args.video_dir.resolve(),
                args.render_dir.resolve(),
            )
        )
    except (OSError, ValueError) as error:
        print(f"error: {error}")
        return 2
    _write_json(args.output, [item.model_dump() for item in items])
    print(f"Wrote {args.output} ({len(items)} videos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
