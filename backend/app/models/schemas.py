from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


VideoId = Literal["A", "B"]


class IngestRequest(BaseModel):
    youtube_url: str = Field(..., description="YouTube video URL (Video A)")
    instagram_url: str = Field(..., description="Instagram Reel URL (Video B)")


class TranscriptSegment(BaseModel):
    start: float
    text: str


class VideoMetadata(BaseModel):
    video_id: VideoId
    platform: Literal["youtube", "instagram"]
    source_url: str
    title: str | None = None
    creator: str | None = None
    follower_count: int | None = None
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    engagement_rate: float | None = None
    hashtags: list[str] = Field(default_factory=list)
    upload_date: str | None = None
    duration_seconds: float | None = None
    thumbnail_url: str | None = None
    transcript: list[TranscriptSegment] = Field(default_factory=list)
    transcript_text: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    session_id: str
    videos: list[VideoMetadata]
    chunk_count: int
    message: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class SourceCitation(BaseModel):
    video_id: VideoId
    chunk_index: int
    platform: str
    excerpt: str
    source_url: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]


class HealthResponse(BaseModel):
    status: str
    has_openai_key: bool
