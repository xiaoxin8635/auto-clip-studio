import json
from pathlib import Path

import pytest

from app.evaluation import (
    Annotation,
    EvaluationItem,
    EvaluatedSegment,
    IdealSegment,
    evaluate,
    evaluate_video,
    load_annotations,
    load_results,
    main,
    render_report,
)


def annotation() -> Annotation:
    return Annotation(
        video="podcast-01.mp4",
        duration_ms=600_000,
        ideal_segments=[
            IdealSegment(title="观点 A", start_ms=120_000, end_ms=165_000, reason="完整"),
            IdealSegment(title="观点 B", start_ms=300_000, end_ms=330_000),
        ],
    )


def result() -> EvaluationItem:
    return EvaluationItem(
        video="podcast-01.mp4",
        candidates=[
            EvaluatedSegment(title="候选 1", start_ms=121_000, end_ms=166_000),
            EvaluatedSegment(title="候选 2", start_ms=302_000, end_ms=331_000),
        ],
        transcript_usable=True,
        rendered=True,
        analysis_ms=180_000,
    )


def test_evaluate_matches_and_boundary_errors() -> None:
    metrics = evaluate_video(annotation(), result())

    assert metrics.hit_count == 2
    assert [match.overlap_ms for match in metrics.matches] == [44_000, 28_000]
    assert metrics.mean_boundary_error_ms == pytest.approx(1_250.0)


def test_evaluate_rejects_missing_results() -> None:
    with pytest.raises(ValueError, match="missing results: podcast-01.mp4"):
        evaluate([annotation()], [])


def test_evaluate_rejects_segment_exceeding_duration() -> None:
    invalid = annotation()
    invalid.ideal_segments[0].end_ms = 600_001
    with pytest.raises(ValueError, match="exceeds video duration"):
        evaluate_video(invalid, result())


def test_loaders_reject_duplicate_and_invalid_json(tmp_path: Path) -> None:
    annotations = tmp_path / "annotations.json"
    results = tmp_path / "results.json"
    annotations.write_text(
        json.dumps([annotation().model_dump(), annotation().model_dump()]),
        encoding="utf-8",
    )
    results.write_text(json.dumps([result().model_dump()]), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate annotation videos"):
        load_annotations(annotations)
    with pytest.raises(ValueError, match="Cannot read results"):
        load_results(tmp_path / "missing.json")


def test_report_and_cli_create_markdown(tmp_path: Path) -> None:
    metrics = evaluate([annotation()], [result()])
    report = render_report(metrics)

    assert "选段命中视频：1/1" in report
    assert "平均边界误差：1.25 秒" in report

    annotations = tmp_path / "annotations.json"
    results = tmp_path / "results.json"
    output = tmp_path / "report.md"
    annotations.write_text(json.dumps([annotation().model_dump()], ensure_ascii=False), encoding="utf-8")
    results.write_text(json.dumps([result().model_dump()], ensure_ascii=False), encoding="utf-8")

    assert main([str(annotations), str(results), "--output", str(output)]) == 0
    assert "状态：已执行。" in output.read_text(encoding="utf-8")
