from __future__ import annotations

import asyncio

from .config import get_settings
from .db import session_scope
from .models import Project, Segment
from .providers import ProviderError, create_provider
from .schemas import ProviderResult
from .state_machine import advance, fail


def run_analysis(project_id: str) -> None:
    asyncio.run(analyze_project(project_id))


async def analyze_project(project_id: str) -> None:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if project is None or project.status not in {"transcribing", "failed"}:
            return
        if project.status == "failed":
            advance(project, "transcribing")
        try:
            provider = create_provider(get_settings())
            result = await provider.analyze(project.source_path, project.duration_ms)
            validate_result(result, project.duration_ms)
            advance(project, "selecting")
            project.transcript = result.transcript.model_dump()
            project.segments.clear()
            for candidate in result.segments:
                project.segments.append(
                    Segment(
                        title=candidate.title,
                        rationale=candidate.rationale,
                        start_ms=candidate.start_ms,
                        end_ms=candidate.end_ms,
                        caption_text=candidate.caption_text,
                        status="proposed",
                    )
                )
            advance(project, "awaiting_review")
        except (ProviderError, ValueError, OSError, TypeError) as exc:
            fail(project, str(exc))


def validate_result(result: ProviderResult, duration_ms: int) -> None:
    if not result.segments:
        raise ValueError("Provider returned no candidate segments")
    for segment in result.segments:
        if segment.end_ms <= segment.start_ms:
            raise ValueError(f"Invalid segment boundaries: {segment.title}")
        if duration_ms and segment.end_ms > duration_ms:
            raise ValueError(f"Segment exceeds source duration: {segment.title}")
