"""Fetch transcripts + metadata from YouTube and Instagram via yt-dlp."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from app.config import settings
from app.models.schemas import TranscriptSegment, VideoId, VideoMetadata

HASHTAG_RE = re.compile(r"#\w+")


def _run_ytdlp(url: str, extra_args: list[str] | None = None) -> dict[str, Any]:
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--no-warnings",
        *(extra_args or []),
        url,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp failed for {url}: {result.stderr.strip() or result.stdout.strip()}"
        )
    line = result.stdout.strip().splitlines()[-1]
    return json.loads(line)


def _extract_hashtags(text: str, tags: list[str] | None) -> list[str]:
    found = {t.lower() for t in (tags or [])}
    for match in HASHTAG_RE.findall(text or ""):
        found.add(match.lower())
    return sorted(found)


def _compute_engagement(views: int | None, likes: int | None, comments: int | None) -> float | None:
    if not views or views <= 0:
        return None
    likes = likes or 0
    comments = comments or 0
    return round(((likes + comments) / views) * 100, 4)


def _youtube_transcript(video_id: str) -> list[TranscriptSegment]:
    try:
        raw = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable):
        try:
            listing = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = listing.find_generated_transcript(["en"])
            raw = transcript.fetch()
        except Exception:
            return []
    return [TranscriptSegment(start=float(item["start"]), text=item["text"].strip()) for item in raw if item.get("text")]


def fetch_youtube(url: str, video_id: VideoId = "A") -> VideoMetadata:
    info = _run_ytdlp(url)
    yt_id = info.get("id", "")
    segments = _youtube_transcript(yt_id) if yt_id else []

    if not segments:
        desc = info.get("description") or ""
        if desc:
            segments = [TranscriptSegment(start=0.0, text=desc[:4000])]

    if not segments:
        segments = _whisper_transcribe(url)

    transcript_text = " ".join(s.text for s in segments)
    views = info.get("view_count")
    likes = info.get("like_count")
    comments = info.get("comment_count")

    return VideoMetadata(
        video_id=video_id,
        platform="youtube",
        source_url=url,
        title=info.get("title"),
        creator=info.get("uploader") or info.get("channel"),
        follower_count=info.get("channel_follower_count"),
        views=views,
        likes=likes,
        comments=comments,
        engagement_rate=_compute_engagement(views, likes, comments),
        hashtags=_extract_hashtags(info.get("description") or "", info.get("tags")),
        upload_date=info.get("upload_date"),
        duration_seconds=info.get("duration"),
        thumbnail_url=info.get("thumbnail"),
        transcript=segments,
        transcript_text=transcript_text,
        extra={"youtube_id": yt_id},
    )


def _try_download_subtitles(url: str) -> list[TranscriptSegment]:
    """Download subtitles/captions with yt-dlp when API transcript missing (Instagram)."""
    out_dir = settings.downloads_path
    template = str(out_dir / "%(id)s")
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-sub",
        "--write-sub",
        "--sub-langs",
        "en.*,en",
        "--sub-format",
        "json3/vtt/best",
        "-o",
        template,
        "--no-warnings",
        url,
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)

    segments: list[TranscriptSegment] = []
    for path in out_dir.glob("*.json3"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            events = data.get("events") or []
            for ev in events:
                segs = ev.get("segs") or []
                text = "".join(s.get("utf8", "") for s in segs).strip()
                if text and text != "\n":
                    segments.append(
                        TranscriptSegment(start=float(ev.get("tStartMs", 0)) / 1000.0, text=text)
                    )
        except Exception:
            continue
        finally:
            path.unlink(missing_ok=True)

    for path in out_dir.glob("*.vtt"):
        try:
            content = path.read_text(encoding="utf-8")
            for block in content.split("\n\n"):
                lines = [ln for ln in block.splitlines() if ln and "-->" not in ln and not ln.startswith("WEBVTT")]
                if lines:
                    segments.append(TranscriptSegment(start=0.0, text=" ".join(lines)))
        except Exception:
            continue
        finally:
            path.unlink(missing_ok=True)

    return segments


def _whisper_transcribe(url: str) -> list[TranscriptSegment]:
    """yt-dlp audio extract + faster-whisper (optional, ENABLE_WHISPER=true)."""
    if not settings.enable_whisper:
        return []

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return []

    out_dir = settings.downloads_path
    for old in out_dir.glob("*"):
        if old.is_file() and old.suffix in (".mp3", ".m4a", ".webm", ".wav"):
            old.unlink(missing_ok=True)

    template = str(out_dir / "%(id)s")
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format",
        "mp3",
        "-o",
        template,
        "--no-warnings",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode != 0:
        return []

    audio_files = list(out_dir.glob("*.mp3")) + list(out_dir.glob("*.m4a"))
    if not audio_files:
        return []

    audio_path = audio_files[0]
    try:
        model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        parts, _ = model.transcribe(str(audio_path), vad_filter=True)
        segments = [
            TranscriptSegment(start=float(p.start), text=p.text.strip())
            for p in parts
            if p.text and p.text.strip()
        ]
        return segments
    finally:
        audio_path.unlink(missing_ok=True)


def fetch_instagram(url: str, video_id: VideoId = "B") -> VideoMetadata:
    info = _run_ytdlp(url)
    segments = _try_download_subtitles(url)
    description = info.get("description") or ""

    if not segments:
        segments = _whisper_transcribe(url)

    if not segments and description:
        segments = [TranscriptSegment(start=0.0, text=description)]

    if settings.enable_whisper and description and segments:
        caption_only = len(segments) == 1 and segments[0].text.strip() == description.strip()
        if caption_only:
            whisper_segments = _whisper_transcribe(url)
            if whisper_segments:
                segments = whisper_segments

    transcript_text = " ".join(s.text for s in segments)
    views = info.get("view_count") or info.get("play_count")
    likes = info.get("like_count")
    comments = info.get("comment_count")

    creator = info.get("uploader") or info.get("channel") or info.get("uploader_id")
    follower_count = info.get("channel_follower_count")

    return VideoMetadata(
        video_id=video_id,
        platform="instagram",
        source_url=url,
        title=info.get("title") or (description[:80] if description else None),
        creator=creator,
        follower_count=follower_count,
        views=views,
        likes=likes,
        comments=comments,
        engagement_rate=_compute_engagement(views, likes, comments),
        hashtags=_extract_hashtags(description, info.get("tags")),
        upload_date=info.get("upload_date") or info.get("timestamp"),
        duration_seconds=info.get("duration"),
        thumbnail_url=info.get("thumbnail"),
        transcript=segments,
        transcript_text=transcript_text,
        extra={"instagram_id": info.get("id")},
    )


def fetch_both(youtube_url: str, instagram_url: str) -> list[VideoMetadata]:
    if "youtube.com" not in youtube_url and "youtu.be" not in youtube_url:
        raise ValueError("Video A must be a YouTube URL")
    if "instagram.com" not in instagram_url:
        raise ValueError("Video B must be an Instagram Reel URL")

    return [
        fetch_youtube(youtube_url, "A"),
        fetch_instagram(instagram_url, "B"),
    ]
