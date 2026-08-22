from __future__ import annotations

from .models import Project, Segment
from .schemas import SegmentOut, Transcript


def segment_to_out(segment: Segment) -> SegmentOut:
    return SegmentOut(
        id=segment.id,
        title=segment.title,
        rationale=segment.rationale,
        start_ms=segment.start_ms,
        end_ms=segment.end_ms,
        caption_text=segment.caption_text,
        status=segment.status,
        download_url=(
            f"/api/projects/{segment.project_id}/segments/{segment.id}/download"
            if segment.output_path
            else None
        ),
    )


def project_to_out(project: Project) -> dict:
    cues = project.transcript.get("cues", []) if project.transcript else []
    transcript_text = " ".join(cue.get("text", "") for cue in cues).strip()
    return {
        "id": project.id,
        "status": project.status,
        "source_filename": project.source_filename,
        "duration_ms": project.duration_ms,
        "transcript_text": transcript_text,
        "error_message": project.error_message,
        "segments": [segment_to_out(segment).model_dump() for segment in project.segments],
    }


def validated_transcript(value: dict | None) -> Transcript | None:
    return Transcript.model_validate(value) if value is not None else None
