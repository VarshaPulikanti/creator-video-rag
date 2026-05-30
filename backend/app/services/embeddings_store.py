"""Chunk transcripts, embed with OpenAI, persist in ChromaDB tagged by video_id."""

from __future__ import annotations

import uuid
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.models.schemas import VideoMetadata


def _metadata_doc(video: VideoMetadata) -> Document:
    """Structured metadata as a retrievable document for factual Q&A."""
    lines = [
        f"video_id: {video.video_id}",
        f"platform: {video.platform}",
        f"source_url: {video.source_url}",
        f"title: {video.title or 'unknown'}",
        f"creator: {video.creator or 'unknown'}",
        f"follower_count: {video.follower_count if video.follower_count is not None else 'unknown'}",
        f"views: {video.views if video.views is not None else 'unknown'}",
        f"likes: {video.likes if video.likes is not None else 'unknown'}",
        f"comments: {video.comments if video.comments is not None else 'unknown'}",
        f"engagement_rate_percent: {video.engagement_rate if video.engagement_rate is not None else 'unknown'}",
        f"hashtags: {', '.join(video.hashtags) if video.hashtags else 'none'}",
        f"upload_date: {video.upload_date or 'unknown'}",
        f"duration_seconds: {video.duration_seconds if video.duration_seconds is not None else 'unknown'}",
    ]
    return Document(
        page_content="\n".join(lines),
        metadata={
            "video_id": video.video_id,
            "platform": video.platform,
            "chunk_index": -1,
            "chunk_type": "metadata",
            "source_url": video.source_url,
        },
    )


def _hook_doc(video: VideoMetadata) -> Document | None:
    """First ~5s of transcript — tagged for hook comparison queries."""
    hook_parts: list[str] = []
    for seg in video.transcript:
        if seg.start <= 5.0:
            hook_parts.append(seg.text)
    hook_text = " ".join(hook_parts).strip()
    if not hook_text:
        return None
    return Document(
        page_content=f"[HOOK first 5 seconds — Video {video.video_id}]\n{hook_text}",
        metadata={
            "video_id": video.video_id,
            "platform": video.platform,
            "chunk_index": 0,
            "chunk_type": "hook",
            "source_url": video.source_url,
        },
    )


def _transcript_docs(video: VideoMetadata) -> list[Document]:
    if not video.transcript_text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(video.transcript_text)
    docs: list[Document] = []
    for idx, chunk in enumerate(chunks):
        docs.append(
            Document(
                page_content=chunk,
                metadata={
                    "video_id": video.video_id,
                    "platform": video.platform,
                    "chunk_index": idx,
                    "chunk_type": "transcript",
                    "source_url": video.source_url,
                    "title": video.title or "",
                    "creator": video.creator or "",
                },
            )
        )
    return docs


def build_collection_name(session_id: str) -> str:
    safe = session_id.replace("-", "")[:32]
    return f"session_{safe}"


def ingest_videos(session_id: str, videos: list[VideoMetadata]) -> int:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for embeddings")

    all_docs: list[Document] = []
    for video in videos:
        all_docs.append(_metadata_doc(video))
        hook = _hook_doc(video)
        if hook:
            all_docs.append(hook)
        all_docs.extend(_transcript_docs(video))

    if not all_docs:
        raise ValueError("No content to embed — check transcript extraction")

    embeddings = OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )

    collection = build_collection_name(session_id)
    Chroma.from_documents(
        documents=all_docs,
        embedding=embeddings,
        collection_name=collection,
        persist_directory=str(settings.chroma_path),
    )
    return len(all_docs)


def get_vectorstore(session_id: str) -> Chroma:
    embeddings = OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )
    return Chroma(
        collection_name=build_collection_name(session_id),
        embedding_function=embeddings,
        persist_directory=str(settings.chroma_path),
    )


def new_session_id() -> str:
    return str(uuid.uuid4())
