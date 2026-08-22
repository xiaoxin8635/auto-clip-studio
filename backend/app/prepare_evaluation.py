from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

import httpx
from pydantic import BaseModel, Field, ValidationError


SEARCH_URL = "https://images-api.nasa.gov/search"


class DraftSegment(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    reason: str = Field(default="Draft generated from official captions", max_length=1000)


class DraftAnnotation(BaseModel):
    video: str = Field(min_length=1, max_length=255)
    duration_ms: int = Field(gt=0)
    ideal_segments: list[DraftSegment] = Field(min_length=1)


@dataclass(frozen=True)
class NasaAsset:
    nasa_id: str
    title: str
    collection_url: str
    caption_url: str | None


@dataclass(frozen=True)
class MediaFile:
    url: str
    variant: str


class PreparationError(RuntimeError):
    pass


def search_assets(client: httpx.Client, query: str, limit: int) -> list[NasaAsset]:
    params = {"q": query, "media_type": "video", "page_size": min(max(limit * 3, 10), 50)}
    response = client.get(SEARCH_URL, params=params)
    response.raise_for_status()
    payload = response.json()
    items = payload.get("collection", {}).get("items", [])
    assets: list[NasaAsset] = []
    for item in items:
        data_list = item.get("data") or []
        if not data_list:
            continue
        data = data_list[0]
        nasa_id = str(data.get("nasa_id") or "")
        title = str(data.get("title") or nasa_id)
        collection_url = str(item.get("href") or "")
        if not nasa_id or not collection_url:
            continue
        caption_url = next(
            (
                str(link.get("href"))
                for link in item.get("links") or []
                if str(link.get("href", "")).lower().endswith(".srt")
            ),
            None,
        )
        assets.append(
            NasaAsset(
                nasa_id=nasa_id,
                title=title,
                collection_url=collection_url,
                caption_url=normalize_asset_url(caption_url) if caption_url else None,
            )
        )
        if len(assets) >= limit:
            break
    return assets


def normalize_asset_url(url: str | None) -> str | None:
    if url is None:
        return None
    parsed = url.split("//", 1)
    if len(parsed) != 2:
        return url
    return f"https://{quote(unquote(parsed[1]), safe='/:~()?=&,')}"


def media_files(client: httpx.Client, asset: NasaAsset) -> list[MediaFile]:
    response = client.get(asset.collection_url)
    response.raise_for_status()
    urls = response.json()
    if not isinstance(urls, list):
        raise PreparationError(f"Invalid asset collection for {asset.nasa_id}")
    files = []
    for url in urls:
        if not isinstance(url, str) or "~" not in url or not url.lower().endswith(".mp4"):
            continue
        variant = url.rsplit("~", 1)[-1].removesuffix(".mp4")
        files.append(MediaFile(url=normalize_asset_url(url) or "", variant=variant))
    return files


def choose_media(files: list[MediaFile], max_variant: str) -> MediaFile:
    allowed = ["preview", "small", "mobile", "medium"]
    if max_variant not in allowed:
        raise PreparationError(f"Unsupported media variant: {max_variant}")
    ceiling = allowed.index(max_variant)
    acceptable = [file for file in files if file.variant in allowed[: ceiling + 1]]
    if not acceptable:
        raise PreparationError("No downloadable MP4 variant was found")
    priority = {"medium": 3, "mobile": 2, "small": 1, "preview": 0}
    return max(acceptable, key=lambda file: priority[file.variant])


def safe_filename(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "-", value.strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-.")
    if not cleaned:
        raise PreparationError("Asset title cannot be converted to a safe filename")
    return f"{cleaned[:100]}.mp4"


def download_file(client: httpx.Client, url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    with client.stream("GET", url) as response:
        response.raise_for_status()
        with temporary.open("wb") as output:
            for chunk in response.iter_bytes(1024 * 256):
                output.write(chunk)
    temporary.replace(destination)


def parse_srt(content: str) -> list[tuple[int, int, str]]:
    blocks = re.split(r"\r?\n\r?\n", content.strip(), flags=re.MULTILINE)
    cues: list[tuple[int, int, str]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start, end = parse_srt_timestamps(lines[1])
        text = " ".join(line for line in lines[2:] if not line.isdigit())
        if text and end > start:
            cues.append((start, end, text))
    return cues


def parse_srt_timestamps(line: str) -> tuple[int, int]:
    match = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", line)
    if not match:
        raise PreparationError(f"Invalid caption timing: {line}")
    values = [int(value) for value in match.groups()]
    start = values[0] * 3_600_000 + values[1] * 60_000 + values[2] * 1000 + values[3]
    end = values[4] * 3_600_000 + values[5] * 60_000 + values[6] * 1000 + values[7]
    return start, end


def make_draft(cues: list[tuple[int, int, str]], duration_ms: int, segment_count: int) -> list[DraftSegment]:
    if not cues:
        raise PreparationError("Caption file contains no readable cues")
    if duration_ms <= 0:
        raise PreparationError("Video duration must be positive")
    target = max(20_000, min(90_000, duration_ms // segment_count))
    chunks: list[list[tuple[int, int, str]]] = []
    current: list[tuple[int, int, str]] = []
    for cue in cues:
        current.append(cue)
        span = current[-1][1] - current[0][0]
        if span >= target or len(current) >= 10:
            chunks.append(current)
            current = []
    if current:
        if chunks and len(current) < 3:
            chunks[-1].extend(current)
        else:
            chunks.append(current)
    chunks = [chunk for chunk in chunks if chunk[-1][1] - chunk[0][0] >= 10_000]
    if not chunks:
        raise PreparationError("Captions are too short to create draft segments")
    selected = sorted(chunks, key=lambda chunk: len(" ".join(cue[2] for cue in chunk)), reverse=True)[:segment_count]
    selected.sort(key=lambda chunk: chunk[0][0])
    drafts = []
    for chunk in selected:
        start = chunk[0][0]
        end = min(chunk[-1][1], duration_ms)
        title = " ".join(cue[2] for cue in chunk[:2]).strip()
        drafts.append(
            DraftSegment(
                title=(title[:120] or "Caption-based draft segment"),
                start_ms=start,
                end_ms=end,
                reason="Draft generated from official captions; review wording and boundaries.",
            )
        )
    return drafts


def probe_duration(path: Path) -> int:
    try:
        import imageio_ffmpeg

        command = [imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)]
    except Exception as exc:
        raise PreparationError("FFmpeg is unavailable for duration probing") from exc
    import subprocess

    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", completed.stderr)
    if not match:
        raise PreparationError("Could not read downloaded media duration")
    hours, minutes, seconds = match.groups()
    return int((int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000)


def prepare(query: str, count: int, max_variant: str, output_dir: Path) -> list[DraftAnnotation]:
    video_dir = output_dir / "videos"
    caption_dir = output_dir / "captions"
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        candidates = [asset for asset in search_assets(client, query, count * 3) if asset.caption_url]
        annotations: list[DraftAnnotation] = []
        for asset in candidates:
            if len(annotations) >= count:
                break
            try:
                media = choose_media(media_files(client, asset), max_variant)
                filename = safe_filename(asset.nasa_id)
                video_path = video_dir / filename
                caption_path = caption_dir / f"{Path(filename).stem}.srt"
                download_file(client, media.url, video_path)
                download_file(client, asset.caption_url or "", caption_path)
                duration = probe_duration(video_path)
                segments = make_draft(parse_srt(caption_path.read_text(encoding="utf-8-sig")), duration, 5)
                annotations.append(
                    DraftAnnotation(video=filename, duration_ms=duration, ideal_segments=segments)
                )
            except (httpx.HTTPError, PreparationError, OSError, ValidationError) as error:
                print(f"Skipped {asset.nasa_id}: {error}", flush=True)
                continue
        if not annotations:
            raise PreparationError("No caption-backed media could be prepared")
        annotation_path = output_dir / "annotations.json"
        annotation_path.write_text(
            json.dumps([annotation.model_dump() for annotation in annotations], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return annotations


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download caption-backed NASA evaluation media and draft annotations")
    parser.add_argument("--query", required=True)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--max-variant", choices=["preview", "small", "mobile", "medium"], default="mobile")
    parser.add_argument("--output", type=Path, default=Path(".local/evaluation"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        annotations = prepare(args.query, args.count, args.max_variant, args.output)
    except (PreparationError, ValueError) as error:
        print(f"error: {error}")
        return 2
    print(f"Prepared {len(annotations)} videos under {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
