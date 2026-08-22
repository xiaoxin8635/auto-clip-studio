from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class MediaToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class MediaInfo:
    duration_ms: int
    width: int
    height: int


def ffmpeg_path() -> str:
    configured = shutil.which("ffmpeg")
    if configured:
        return configured
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - environment-specific
        raise MediaToolError("FFmpeg is not installed or available on PATH") from exc


def ffprobe_path() -> str:
    configured = shutil.which("ffprobe")
    if configured:
        return configured
    ffmpeg = Path(ffmpeg_path())
    candidate = ffmpeg.with_name("ffprobe.exe" if ffmpeg.name.lower().endswith(".exe") else "ffprobe")
    if candidate.exists():
        return str(candidate)
    raise MediaToolError("FFprobe is not installed or available on PATH")


def probe_media(path: Path) -> MediaInfo:
    if ffprobe_available():
        return probe_with_ffprobe(path)
    return probe_with_ffmpeg(path)


def ffprobe_available() -> bool:
    try:
        ffprobe_path()
        return True
    except MediaToolError:
        return False


def probe_with_ffprobe(path: Path) -> MediaInfo:
    try:
        completed = subprocess.run(
            [
                ffprobe_path(),
                "-v",
                "error",
                "-show_entries",
                "stream=width,height:format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise MediaToolError(f"Unable to probe video metadata: {exc}") from exc
    try:
        payload = json.loads(completed.stdout)
        streams = payload.get("streams") or []
        valid_streams = [stream for stream in streams if stream.get("width") and stream.get("height")]
        duration = float(payload["format"]["duration"])
        stream = valid_streams[0]
        return MediaInfo(int(duration * 1000), int(stream["width"]), int(stream["height"]))
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise MediaToolError("Uploaded file does not contain readable video metadata") from exc


def probe_with_ffmpeg(path: Path) -> MediaInfo:
    try:
        completed = subprocess.run(
            [ffmpeg_path(), "-i", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = completed.stderr
        duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", output)
        size_match = re.search(r",\s*(\d{2,5})x(\d{2,5})", output)
        if not duration_match or not size_match:
            raise MediaToolError("Uploaded file does not contain readable video metadata")
        hours, minutes, seconds = duration_match.groups()
        duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        return MediaInfo(int(duration * 1000), int(size_match.group(1)), int(size_match.group(2)))
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        if isinstance(exc, MediaToolError):
            raise
        raise MediaToolError(f"Unable to probe video metadata: {exc}") from exc
