from __future__ import annotations

from .model_provider import OllamaProvider


class EmbeddingService:
    """Optional semantic adapter. CRM lexical search never depends on it."""

    def __init__(self, provider: OllamaProvider) -> None:
        self.provider = provider
        self.dimension: int | None = None

    def embed(self, text: str) -> list[float] | None:
        vector = self.provider.embed(text)
        if vector is not None:
            self.dimension = len(vector)
        return vector
