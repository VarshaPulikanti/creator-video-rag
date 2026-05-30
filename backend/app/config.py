from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    chunk_size: int = 500
    chunk_overlap: int = 80
    retrieval_k: int = 6

    chroma_persist_dir: str = "data/chroma"
    memory_window: int = 10

    # yt-dlp + Whisper path when captions/caption text are missing
    enable_whisper: bool = False
    whisper_model: str = "base"

    @property
    def chroma_path(self) -> Path:
        path = BACKEND_DIR / self.chroma_persist_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def downloads_path(self) -> Path:
        path = BACKEND_DIR / "data" / "downloads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def sessions_path(self) -> Path:
        path = BACKEND_DIR / "data" / "sessions"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
