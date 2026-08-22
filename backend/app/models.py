from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid.uuid4().hex


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    status: Mapped[str] = mapped_column(String(32), index=True)
    source_filename: Mapped[str | None] = mapped_column(String(255))
    source_path: Mapped[str | None] = mapped_column(String(1024))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    transcript: Mapped[str | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    segments: Mapped[list[Segment]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Segment.start_ms",
    )


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    rationale: Mapped[str] = mapped_column(String(1000))
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    caption_text: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(32), default="proposed")
    output_path: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    project: Mapped[Project] = relationship(back_populates="segments")
