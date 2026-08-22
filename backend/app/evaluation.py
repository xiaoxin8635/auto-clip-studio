from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


class IdealSegment(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    reason: str = Field(default="", max_length=1000)


class Annotation(BaseModel):
    video: str = Field(min_length=1, max_length=255)
    duration_ms: int = Field(gt=0)
    ideal_segments: list[IdealSegment] = Field(min_length=1)


class EvaluatedSegment(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)


class EvaluationItem(BaseModel):
    video: str = Field(min_length=1, max_length=255)
    candidates: list[EvaluatedSegment] = Field(default_factory=list)
    transcript_usable: bool = True
    rendered: bool = True
    analysis_ms: int = Field(ge=0)
    failure_reason: str = Field(default="", max_length=1000)


@dataclass(frozen=True)
class SegmentMatch:
    ideal: IdealSegment
    candidate: EvaluatedSegment | None
    overlap_ms: int
    boundary_error_ms: float | None


@dataclass(frozen=True)
class VideoMetrics:
    annotation: Annotation
    item: EvaluationItem
    matches: list[SegmentMatch]
    hit_count: int
    mean_boundary_error_ms: float | None


def load_annotations(path: Path) -> list[Annotation]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read annotations from {path}: {error}") from error
    if not isinstance(raw, list):
        raise ValueError("Annotations file must contain a JSON array")
    try:
        annotations = [Annotation.model_validate(entry) for entry in raw]
    except ValidationError as error:
        raise ValueError(f"Invalid annotation entry: {error}") from error
    _reject_duplicates([item.video for item in annotations], "annotation")
    return annotations


def load_results(path: Path) -> list[EvaluationItem]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read results from {path}: {error}") from error
    if not isinstance(raw, list):
        raise ValueError("Results file must contain a JSON array")
    try:
        results = [EvaluationItem.model_validate(entry) for entry in raw]
    except ValidationError as error:
        raise ValueError(f"Invalid evaluation result: {error}") from error
    _reject_duplicates([item.video for item in results], "result")
    return results


def _reject_duplicates(values: list[str], label: str) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise ValueError(f"Duplicate {label} videos: {', '.join(duplicates)}")


def _overlap_ms(left: IdealSegment, right: EvaluatedSegment) -> int:
    return max(0, min(left.end_ms, right.end_ms) - max(left.start_ms, right.start_ms))


def _boundary_error_ms(ideal: IdealSegment, candidate: EvaluatedSegment) -> float:
    return (abs(ideal.start_ms - candidate.start_ms) + abs(ideal.end_ms - candidate.end_ms)) / 2


def evaluate_video(annotation: Annotation, item: EvaluationItem) -> VideoMetrics:
    if annotation.video != item.video:
        raise ValueError(f"Annotation/result video mismatch: {annotation.video} != {item.video}")
    for segment in annotation.ideal_segments:
        if segment.end_ms <= segment.start_ms:
            raise ValueError(f"Ideal segment {segment.title!r} must end after it starts")
        if segment.end_ms > annotation.duration_ms:
            raise ValueError(f"Ideal segment {segment.title!r} exceeds video duration")
    for candidate in item.candidates:
        if candidate.end_ms <= candidate.start_ms:
            raise ValueError(f"Candidate {candidate.title!r} must end after it starts")

    available = list(item.candidates)
    matches: list[SegmentMatch] = []
    for ideal in annotation.ideal_segments:

        def ranking(candidate: EvaluatedSegment) -> tuple[int, float]:
            overlap = _overlap_ms(ideal, candidate)
            error = _boundary_error_ms(ideal, candidate)
            return (overlap, -error)

        ranked = sorted(
            available,
            key=ranking,
            reverse=True,
        )
        selected: EvaluatedSegment | None = None
        for candidate in ranked:
            if _overlap_ms(ideal, candidate) / (ideal.end_ms - ideal.start_ms) >= 0.5:
                selected = candidate
                break
        if selected is None:
            matches.append(SegmentMatch(ideal=ideal, candidate=None, overlap_ms=0, boundary_error_ms=None))
            continue
        available.remove(selected)
        matches.append(
            SegmentMatch(
                ideal=ideal,
                candidate=selected,
                overlap_ms=_overlap_ms(ideal, selected),
                boundary_error_ms=_boundary_error_ms(ideal, selected),
            )
        )

    errors = [match.boundary_error_ms for match in matches if match.boundary_error_ms is not None]
    return VideoMetrics(
        annotation=annotation,
        item=item,
        matches=matches,
        hit_count=sum(match.candidate is not None for match in matches),
        mean_boundary_error_ms=sum(errors) / len(errors) if errors else None,
    )


def evaluate(annotations: list[Annotation], results: list[EvaluationItem]) -> list[VideoMetrics]:
    annotation_videos = {item.video for item in annotations}
    result_videos = {item.video for item in results}
    missing = sorted(annotation_videos - result_videos)
    extra = sorted(result_videos - annotation_videos)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing results: {', '.join(missing)}")
        if extra:
            details.append(f"extra results: {', '.join(extra)}")
        raise ValueError("; ".join(details))
    annotations_by_video = {item.video: item for item in annotations}
    return [evaluate_video(annotations_by_video[item.video], item) for item in results]


def render_report(metrics: list[VideoMetrics]) -> str:
    total = len(metrics)
    videos_with_hit = sum(video.hit_count > 0 for video in metrics)
    usable_transcripts = sum(video.item.transcript_usable for video in metrics)
    rendered = sum(video.item.rendered for video in metrics)
    boundary_errors = [video.mean_boundary_error_ms for video in metrics if video.mean_boundary_error_ms is not None]
    mean_boundary = sum(boundary_errors) / len(boundary_errors) if boundary_errors else None
    mean_analysis_ms = sum(video.item.analysis_ms for video in metrics) / total if total else 0

    lines = [
        "# 评测报告",
        "",
        "状态：已执行。",
        "",
        "## 汇总",
        "",
        f"- 选段命中视频：{videos_with_hit}/{total}",
        f"- 字幕可用率：{usable_transcripts / total:.0%}" if total else "- 字幕可用率：N/A",
        f"- 渲染成功率：{rendered / total:.0%}" if total else "- 渲染成功率：N/A",
        f"- 平均边界误差：{mean_boundary / 1000:.2f} 秒" if mean_boundary is not None else "- 平均边界误差：N/A",
        f"- 平均端到端耗时：{mean_analysis_ms / 1000:.2f} 秒",
        "",
        "## 明细",
        "",
        "| 视频 | 理想片段命中 | 边界误差 | 字幕可用 | 渲染成功 | 端到端耗时 | 失败原因 |",
        "|---|---:|---:|---|---|---:|---|",
    ]
    for video in metrics:
        boundary = f"{video.mean_boundary_error_ms / 1000:.2f}s" if video.mean_boundary_error_ms is not None else "N/A"
        lines.append(
            f"| {video.annotation.video} | {video.hit_count}/{len(video.annotation.ideal_segments)} "
            f"| {boundary} | {'是' if video.item.transcript_usable else '否'} "
            f"| {'是' if video.item.rendered else '否'} | {video.item.analysis_ms / 1000:.2f}s "
            f"| {video.item.failure_reason or '-'} |"
        )
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize real-provider evaluation results")
    parser.add_argument("annotations", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/evaluation-report.md"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        metrics = evaluate(load_annotations(args.annotations), load_results(args.results))
    except ValueError as error:
        print(f"error: {error}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(metrics), encoding="utf-8")
    print(f"Wrote {args.output} ({len(metrics)} videos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
