from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///data/salespod.db"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "qwen2.5:3b"
    ollama_embed_model: str = "nomic-embed-text"
    dataset_as_of: datetime = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    seed: int = 424242
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Settings:
        raw_as_of = os.getenv("DATASET_AS_OF")
        as_of = cls.dataset_as_of
        if raw_as_of:
            as_of = datetime.fromisoformat(raw_as_of.replace("Z", "+00:00"))
            if as_of.tzinfo is None:
                as_of = as_of.replace(tzinfo=UTC)
            as_of = as_of.astimezone(UTC)
        return cls(
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", cls.ollama_base_url).rstrip("/"),
            ollama_chat_model=os.getenv("OLLAMA_CHAT_MODEL", cls.ollama_chat_model),
            ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", cls.ollama_embed_model),
            dataset_as_of=as_of,
            seed=int(os.getenv("SALES_POD_SEED", str(cls.seed))),
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
        )

    def ensure_database_parent(self) -> None:
        """Create the local parent directory for SQLite URLs only."""
        if self.database_url.startswith("sqlite:///") and ":memory:" not in self.database_url:
            path = Path(self.database_url.removeprefix("sqlite:///"))
            path.parent.mkdir(parents=True, exist_ok=True)
