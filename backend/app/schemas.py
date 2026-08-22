from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    pass


class TranscriptCue(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = Field(min_length=1)


class Transcript(BaseModel):
    language: str = Field(default="zh", min_length=1)
    cues: list[TranscriptCue] = Field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(cue.text for cue in self.cues).strip()


class ProviderSegment(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=1000)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    caption_text: str = Field(default="", max_length=2000)


class ProviderResult(BaseModel):
    transcript: Transcript
    segments: list[ProviderSegment] = Field(min_length=1)


class SegmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, gt=0)


class SegmentOut(BaseModel):
    id: str
    title: str
    rationale: str
    start_ms: int
    end_ms: int
    caption_text: str
    status: str
    download_url: str | None = None


class ProjectOut(BaseModel):
    id: str
    status: str
    source_filename: str | None
    duration_ms: int
    transcript_text: str
    error_message: str | None
    segments: list[SegmentOut]
