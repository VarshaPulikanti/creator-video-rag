"""LangChain RAG with retrieval, streaming, citations, and conversational memory."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

from app.config import settings
from app.models.schemas import SourceCitation, VideoId
from app.services.embeddings_store import get_vectorstore
from app.services.session_store import append_chat, get_chat_history, get_videos

SYSTEM_PROMPT = """You are a creator analytics assistant comparing two short-form videos:
- Video A: YouTube
- Video B: Instagram Reel

Use ONLY the provided context (transcript chunks + metadata). If data is missing, say so clearly.

When comparing engagement, use engagement_rate_percent from metadata when available.
For hook analysis, focus on transcript content from the first ~5 seconds when timestamps exist.

Always be specific and actionable. Reference Video A or Video B by name.

At the end of your answer, you do NOT need to list sources — the UI shows citations separately.
"""

ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        (
            "human",
            "Context from retrieved chunks:\n{context}\n\n"
            "Creator question: {input}\n\n"
            "Answer:",
        ),
    ]
)

REPHRASE_PROMPT = ChatPromptTemplate.from_messages(
    [
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        (
            "human",
            "Given the conversation above, rewrite the latest user question as a standalone "
            "search query for retrieving relevant transcript/metadata chunks about Video A (YouTube) "
            "or Video B (Instagram). Output only the query.",
        ),
    ]
)


def _docs_to_citations(docs: list[Document]) -> list[SourceCitation]:
    seen: set[tuple[str, int]] = set()
    citations: list[SourceCitation] = []
    for doc in docs:
        meta = doc.metadata or {}
        vid = meta.get("video_id", "?")
        chunk_index = int(meta.get("chunk_index", 0))
        key = (vid, chunk_index)
        if key in seen:
            continue
        seen.add(key)
        excerpt = doc.page_content[:280] + ("…" if len(doc.page_content) > 280 else "")
        video_label: VideoId = "A" if vid == "A" else "B"
        citations.append(
            SourceCitation(
                video_id=video_label,
                chunk_index=chunk_index,
                platform=str(meta.get("platform", "unknown")),
                excerpt=excerpt,
                source_url=meta.get("source_url"),
            )
        )
    return citations


def _history_to_messages(history: list[dict]) -> list:
    messages = []
    for item in history:
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        elif item["role"] == "assistant":
            messages.append(AIMessage(content=item["content"]))
    return messages


def _build_chain(session_id: str):
    llm = ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
        streaming=True,
    )

    retriever = get_vectorstore(session_id).as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.retrieval_k},
    )

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, REPHRASE_PROMPT
    )

    question_answer_chain = create_stuff_documents_chain(llm, ANSWER_PROMPT)
    return create_retrieval_chain(history_aware_retriever, question_answer_chain)


def _format_context_block(videos: list) -> str:
    lines = ["## Video summary (always available)"]
    for v in videos:
        lines.append(
            f"- Video {v.video_id} ({v.platform}): creator={v.creator}, "
            f"followers={v.follower_count}, views={v.views}, likes={v.likes}, "
            f"comments={v.comments}, engagement_rate={v.engagement_rate}%"
        )
    return "\n".join(lines)


async def stream_chat(session_id: str, message: str) -> AsyncGenerator[str, None]:
    """SSE events: token | sources | done | error"""
    if not settings.openai_api_key:
        yield _sse("error", {"message": "OPENAI_API_KEY not configured"})
        return

    videos = get_videos(session_id)
    if not videos:
        yield _sse("error", {"message": "Invalid or expired session_id"})
        return

    history = get_chat_history(session_id)
    chat_history = _history_to_messages(history)

    chain = _build_chain(session_id)
    full_answer: list[str] = []
    retrieved_docs: list[Document] = []

    try:
        async for event in chain.astream_events(
            {"input": message, "chat_history": chat_history},
            version="v2",
        ):
            kind = event.get("event")
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and getattr(chunk, "content", None):
                    token = chunk.content
                    if isinstance(token, str) and token:
                        full_answer.append(token)
                        yield _sse("token", {"content": token})
            elif kind == "on_retriever_end":
                output = event.get("data", {}).get("output")
                if output:
                    retrieved_docs = list(output)

        answer_text = "".join(full_answer).strip()
        if not answer_text:
            # Fallback non-streaming invoke
            result = chain.invoke({"input": message, "chat_history": chat_history})
            answer_text = result.get("answer", "")
            retrieved_docs = result.get("context", []) or retrieved_docs
            yield _sse("token", {"content": answer_text})

        citations = _docs_to_citations(retrieved_docs)
        append_chat(session_id, "user", message)
        append_chat(session_id, "assistant", answer_text)

        yield _sse("sources", {"sources": [c.model_dump() for c in citations]})
        yield _sse("done", {"answer": answer_text})
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})


def chat_sync(session_id: str, message: str) -> tuple[str, list[SourceCitation]]:
    """Non-streaming fallback for testing."""
    videos = get_videos(session_id)
    if not videos:
        raise ValueError("Invalid session")

    history = get_chat_history(session_id)
    chat_history = _history_to_messages(history)
    chain = _build_chain(session_id)
    result = chain.invoke({"input": message, "chat_history": chat_history})
    answer = result.get("answer", "")
    docs = result.get("context", []) or []
    citations = _docs_to_citations(docs)
    append_chat(session_id, "user", message)
    append_chat(session_id, "assistant", answer)
    return answer, citations


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
