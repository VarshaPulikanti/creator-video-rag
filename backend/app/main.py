"""FastAPI backend — ingest videos, embed to Chroma, stream RAG chat."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.models.schemas import ChatRequest, HealthResponse, IngestRequest, IngestResponse
from app.services.embeddings_store import ingest_videos, new_session_id
from app.services.rag_chain import stream_chat
from app.services.session_store import save_session
from app.services.video_fetcher import fetch_both

app = FastAPI(
    title="Creator Video RAG",
    description="Compare YouTube vs Instagram Reels with LangChain RAG",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        has_openai_key=bool(settings.openai_api_key),
    )


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(body: IngestRequest):
    if not settings.openai_api_key:
        raise HTTPException(400, "Set OPENAI_API_KEY in .env before ingesting")

    try:
        videos = fetch_both(body.youtube_url, body.instagram_url)
    except Exception as exc:
        raise HTTPException(422, f"Failed to fetch videos: {exc}") from exc

    session_id = new_session_id()
    try:
        chunk_count = ingest_videos(session_id, videos)
    except Exception as exc:
        raise HTTPException(500, f"Embedding failed: {exc}") from exc

    save_session(session_id, videos)

    return IngestResponse(
        session_id=session_id,
        videos=videos,
        chunk_count=chunk_count,
        message="Videos ingested. Start chatting.",
    )


@app.post("/api/chat/stream")
async def chat_stream(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(400, "Message cannot be empty")

    return EventSourceResponse(stream_chat(body.session_id, body.message.strip()))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
