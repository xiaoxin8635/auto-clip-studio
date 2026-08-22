from __future__ import annotations

from pathlib import Path

from ..schemas import ProviderResult, ProviderSegment, Transcript, TranscriptCue
from .base import AIProvider


class MockProvider(AIProvider):
    async def analyze(self, media_path: Path, duration_ms: int) -> ProviderResult:
        usable_duration = max(duration_ms, 6_000)
        cue_duration = usable_duration // 3
        cues = [
            TranscriptCue(
                start_ms=0,
                end_ms=cue_duration,
                text="欢迎来到本期节目，我们今天聊自动化剪辑的真实工作流。",
            ),
            TranscriptCue(
                start_ms=cue_duration,
                end_ms=cue_duration * 2,
                text="很多团队卡在素材整理和反复试剪，这里最容易被工具接管。",
            ),
            TranscriptCue(
                start_ms=cue_duration * 2,
                end_ms=cue_duration * 3,
                text="最后我们把结果交回给人确认，质量和效率才能同时成立。",
            ),
        ]
        transcript = Transcript(language="zh", cues=cues)
        if duration_ms < 15_000:
            starts = [0]
        else:
            starts = [0, duration_ms // 3, duration_ms * 2 // 3]
        segment_duration = max(2_000, usable_duration // 3)
        titles = ["自动剪辑的真实切入点", "素材整理是最大瓶颈", "人机确认的效率边界"]
        rationales = [
            "直接回应观众对自动化价值的疑问，适合作为开场短片。",
            "指出常见团队痛点，冲突明确，适合社交传播。",
            "总结工作流中的人类判断价值，观点完整。",
        ]
        segments = [
            ProviderSegment(
                title=title,
                rationale=rationale,
                start_ms=start,
                end_ms=min(start + segment_duration, usable_duration),
                caption_text=cues[min(index, 2)].text,
            )
            for index, (title, rationale, start) in enumerate(zip(titles, rationales, starts, strict=True))
        ]
        segments = [segment for segment in segments if segment.end_ms > segment.start_ms + 5_000]
        if not segments:
            raise ValueError("Video is too short for mock segment generation")
        return ProviderResult(transcript=transcript, segments=segments)
