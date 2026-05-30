"""Persist session video metadata + chat history on disk (simple, no Redis needed for demo)."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.models.schemas import VideoMetadata


def _session_file(session_id: str) -> Path:
    return settings.sessions_path / f"{session_id}.json"


def save_session(session_id: str, videos: list[VideoMetadata]) -> None:
    payload = {
        "session_id": session_id,
        "videos": [v.model_dump() for v in videos],
        "chat_history": [],
    }
    _session_file(session_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_session(session_id: str) -> dict | None:
    path = _session_file(session_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_videos(session_id: str) -> list[VideoMetadata]:
    data = load_session(session_id)
    if not data:
        return []
    return [VideoMetadata(**v) for v in data.get("videos", [])]


def append_chat(session_id: str, role: str, content: str) -> list[dict]:
    data = load_session(session_id)
    if not data:
        raise KeyError(f"Unknown session: {session_id}")

    history: list[dict] = data.setdefault("chat_history", [])
    history.append({"role": role, "content": content})

    # Sliding window
    max_messages = settings.memory_window * 2
    if len(history) > max_messages:
        data["chat_history"] = history[-max_messages:]
        history = data["chat_history"]

    _session_file(session_id).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return history


def get_chat_history(session_id: str) -> list[dict]:
    data = load_session(session_id)
    if not data:
        return []
    return data.get("chat_history", [])
