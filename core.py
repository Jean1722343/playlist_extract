from __future__ import annotations

import html
from dataclasses import asdict, dataclass
import re
from pathlib import Path
from typing import Any, Callable, cast

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


DEFAULT_OUTPUT_NAME = "transcripciones_playlist.txt"
TRANSCRIPTS_DIRNAME = "transcripciones"


@dataclass(frozen=True)
class PlaylistVideo:
    index: int
    video_id: str
    title: str
    url: str


def normalize_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_languages(raw: str) -> list[str]:
    languages = [item.strip() for item in raw.split(",") if item.strip()]
    return languages or ["es", "en"]


def transcripts_folder(base_path: Path | None = None) -> Path:
    root_path = base_path or Path.cwd()
    return root_path / TRANSCRIPTS_DIRNAME


def extract_playlist_videos(playlist_url: str) -> list[PlaylistVideo]:
    options: dict[str, Any] = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "ignoreerrors": True,
        "noplaylist": False,
    }

    with yt_dlp.YoutubeDL(cast(Any, options)) as downloader:
        info = downloader.extract_info(playlist_url, download=False)

    entries = info.get("entries") or []
    videos: list[PlaylistVideo] = []

    for position, entry in enumerate(entries, start=1):
        if not entry:
            continue

        video_id = entry.get("id") or entry.get("url")
        if not video_id:
            continue

        title = normalize_text(entry.get("title") or f"Video {position}")
        video_url = entry.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}"
        videos.append(
            PlaylistVideo(
                index=position,
                video_id=video_id,
                title=title,
                url=video_url,
            )
        )

    return videos


def fetch_transcript_lines(video_id: str, preferred_languages: list[str]) -> list[dict[str, Any]]:
    transcript_api = YouTubeTranscriptApi()
    transcript = transcript_api.fetch(video_id, languages=preferred_languages)
    return [asdict(snippet) for snippet in transcript]


def build_transcript_document(
    playlist_url: str,
    videos: list[PlaylistVideo],
    preferred_languages: list[str],
    progress_callback: Callable[[int, int, PlaylistVideo], None] | None = None,
) -> str:
    lines: list[str] = []
    lines.append("TRANSCRIPCIONES DE PLAYLIST DE YOUTUBE")
    lines.append("=" * 40)
    lines.append(f"Playlist: {playlist_url}")
    lines.append(f"Idiomas preferidos: {', '.join(preferred_languages)}")
    lines.append(f"Total de videos detectados: {len(videos)}")
    lines.append("")

    total_videos = len(videos)

    for index, video in enumerate(videos, start=1):
        if progress_callback is not None:
            progress_callback(index, total_videos, video)

        lines.append(f"{video.index}. {video.title}")
        lines.append(f"URL: {video.url}")

        try:
            transcript_lines = fetch_transcript_lines(video.video_id, preferred_languages)
        except Exception as exc:  # noqa: BLE001
            lines.append(f"Transcripción no disponible: {exc}")
            lines.append("")
            continue

        for item in transcript_lines:
            timestamp = format_timestamp(float(item.get("start", 0.0)))
            text = normalize_text(str(item.get("text", "")))
            if text:
                lines.append(f"[{timestamp}] {text}")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def save_transcript_file(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")