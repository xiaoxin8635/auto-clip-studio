from __future__ import annotations

import subprocess
from pathlib import Path

from .config import get_settings
from .db import session_scope
from .media import ffmpeg_path
from .models import Project, Segment
from .state_machine import advance, fail


class RenderError(RuntimeError):
    pass


def run_render(project_id: str, segment_id: str) -> None:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if project is None or project.status != "rendering":
            return
        segment = next((item for item in project.segments if item.id == segment_id), None)
        if segment is None:
            fail(project, "Segment not found during render")
            return
        settings = get_settings()
        render_dir = settings.data_dir / "renders"
        render_dir.mkdir(parents=True, exist_ok=True)
        output = render_dir / f"{project_id}-{segment_id}.mp4"
        try:
            render_segment(Path(project.source_path), output, segment)
            segment.output_path = str(output)
            segment.status = "rendered"
            advance(project, "completed")
        except (RenderError, OSError, subprocess.SubprocessError) as exc:
            output.unlink(missing_ok=True)
            segment.output_path = None
            segment.status = "failed"
            advance(project, "awaiting_review")
            fail(project, f"Render failed: {exc}")
        except Exception:
            output.unlink(missing_ok=True)
            segment.status = "failed"
            advance(project, "awaiting_review")
            fail(project, "Render failed unexpectedly")
            raise


def run_render_batch(project_id: str) -> None:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if project is None or project.status != "rendering":
            return
        settings = get_settings()
        render_dir = settings.data_dir / "renders"
        render_dir.mkdir(parents=True, exist_ok=True)
        failures: list[str] = []
        for segment in project.segments:
            output = render_dir / f"{project_id}-{segment.id}.mp4"
            try:
                render_segment(Path(project.source_path), output, segment)
                segment.output_path = str(output)
                segment.status = "rendered"
            except (RenderError, OSError, subprocess.SubprocessError) as exc:
                output.unlink(missing_ok=True)
                segment.output_path = None
                segment.status = "failed"
                failures.append(f"{segment.title}: {exc}")
        if failures:
            advance(project, "awaiting_review")
            fail(project, f"Render failed for {len(failures)} segment(s): " + "; ".join(failures)[:768])
            return
        advance(project, "completed")


def render_segment(source: Path, output: Path, segment: Segment) -> None:
    if not source.exists():
        raise RenderError("Source video is missing")
    source_resolved = source.resolve()
    output_resolved = output.resolve()
    if get_settings().data_dir.resolve() not in output_resolved.parents:
        raise RenderError("Render output is outside the runtime directory")
    caption_file = output.with_suffix(".caption.txt")
    caption_file.write_text((segment.caption_text or segment.title) + "\n", encoding="utf-8")
    command = [
        ffmpeg_path(),
        "-y",
        "-ss",
        format_seconds(segment.start_ms),
        "-i",
        str(source_resolved),
        "-t",
        format_seconds(max(1, segment.end_ms - segment.start_ms)),
        "-vf",
        (
            "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            f"drawtext=textfile='{escape_drawtext(str(caption_file.resolve()))}':fontcolor=white:fontsize=64:box=1:boxcolor=black@0.55:boxborderw=18:x=(w-text_w)/2:y=h*0.78"
        ),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(output_resolved),
    ]
    try:
        subprocess.run(command, capture_output=True, text=True, timeout=600, check=True)
        if not output.exists() or output.stat().st_size == 0:
            raise RenderError("FFmpeg did not produce an output file")
    except subprocess.TimeoutExpired as exc:
        raise RenderError("Render timed out after 600 seconds") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip().splitlines()[-1:] or ["FFmpeg exited with an error"]
        raise RenderError(detail[0][:300]) from exc
    finally:
        caption_file.unlink(missing_ok=True)


def format_seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.3f}"


def escape_drawtext(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")
