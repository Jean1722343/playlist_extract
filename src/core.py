from __future__ import annotations

import html
import random
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
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
    """Limpia y normaliza texto decodificando entidades HTML y colapsando espacios."""
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def format_timestamp(seconds: float) -> str:
    """Convierte segundos a formato HH:MM:SS o MM:SS."""
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_languages(raw: str) -> list[str]:
    """Parsea una cadena de idiomas separados por coma."""
    languages = [item.strip() for item in raw.split(",") if item.strip()]
    return languages or ["es", "en"]


def transcripts_folder(base_path: Path | None = None) -> Path:
    """Retorna la ruta de la carpeta de transcripciones."""
    root_path = base_path or Path.cwd()
    return root_path / TRANSCRIPTS_DIRNAME


def sanitize_filename(name: str) -> str:
    """Limpia un string para usarlo como nombre de archivo seguro."""
    cleaned = re.sub(r"[^A-Za-z0-9áéíóúñÁÉÍÓÚÑüÜ._\s-]+", "_", name)
    cleaned = re.sub(r"[\s_]+", "_", cleaned).strip("._-")
    return cleaned or "transcripciones_playlist"


def build_output_filename(raw_name: str | None = None) -> str:
    """Genera un nombre de archivo único con timestamp para evitar sobreescrituras.

    Args:
        raw_name: Nombre sugerido del archivo (sin timestamp). Si es vacío, usa el default.

    Returns:
        Nombre de archivo con timestamp: {nombre_limpio}_{YYYY-MM-DD_HH-MM-SS}.txt
    """
    base_name = (raw_name or "").strip() or DEFAULT_OUTPUT_NAME
    stem = Path(base_name).stem
    cleaned_stem = sanitize_filename(stem)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{cleaned_stem}_{timestamp}.txt"


def extract_playlist_title(playlist_url: str) -> str:
    """Extrae el título de una playlist de YouTube usando yt-dlp.

    Args:
        playlist_url: URL completa de la playlist.

    Returns:
        Título de la playlist, o cadena vacía si no se puede obtener.
    """
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "ignoreerrors": True,
        "noplaylist": False,
        "playlist_items": "0",
    }

    try:
        with yt_dlp.YoutubeDL(cast(Any, options)) as downloader:
            info = downloader.extract_info(playlist_url, download=False)
        return normalize_text(info.get("title", "")) if info else ""
    except Exception:  # noqa: BLE001
        return ""


def extract_playlist_videos(playlist_url: str) -> list[PlaylistVideo]:
    """Extrae la lista de videos de una playlist de YouTube.

    Args:
        playlist_url: URL completa de la playlist.

    Returns:
        Lista de PlaylistVideo con la información de cada video.
    """
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "ignoreerrors": True,
        "noplaylist": False,
    }

    with yt_dlp.YoutubeDL(cast(Any, options)) as downloader:
        info = downloader.extract_info(playlist_url, download=False)

    if not info:
        return []

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


def fetch_transcript_lines(video_id: str, preferred_languages: list[str], retries: int = 3) -> list[dict[str, Any]]:
    """Descarga las líneas de transcripción de un video de YouTube con reintentos."""
    transcript_api = YouTubeTranscriptApi()
    
    for attempt in range(retries):
        try:
            # Pausa aleatoria para evitar bloqueos por IP (Rate Limiting)
            delay = random.uniform(2.0, 4.5)
            time.sleep(delay)
            
            transcript = transcript_api.fetch(video_id, languages=preferred_languages)
            return [asdict(snippet) for snippet in transcript]
        except Exception as e:
            if attempt < retries - 1:
                # Si falla, esperamos más tiempo antes del próximo intento (backoff)
                time.sleep(random.uniform(5.0, 10.0))
            else:
                raise e
    return []


def build_transcript_document(
    playlist_url: str,
    videos: list[PlaylistVideo],
    preferred_languages: list[str],
    playlist_title: str = "",
    progress_callback: Callable[[int, int, PlaylistVideo], None] | None = None,
) -> str:
    """Construye el documento de texto con todas las transcripciones.

    Args:
        playlist_url: URL de la playlist.
        videos: Lista de videos a transcribir.
        preferred_languages: Idiomas preferidos para las transcripciones.
        playlist_title: Título de la playlist (opcional).
        progress_callback: Callback para reportar progreso.

    Returns:
        Contenido completo del documento de transcripciones.
    """
    lines: list[str] = []
    lines.append("TRANSCRIPCIONES DE PLAYLIST DE YOUTUBE")
    lines.append("=" * 40)
    if playlist_title:
        lines.append(f"Playlist: {playlist_title}")
    lines.append(f"URL: {playlist_url}")
    lines.append(f"Idiomas preferidos: {', '.join(preferred_languages)}")
    lines.append(f"Total de videos detectados: {len(videos)}")
    lines.append(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    """Guarda el contenido de las transcripciones en un archivo de texto."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")