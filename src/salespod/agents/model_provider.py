from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


class OllamaProvider:
    """Small stdlib-only Ollama adapter; model integrations remain optional."""

    def __init__(
        self,
        *,
        base_url: str,
        chat_model: str,
        embed_model: str,
        timeout: float = 4.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.timeout = timeout

    def available(self) -> bool:
        try:
            request = Request(f"{self.base_url}/api/tags", method="GET")
            with urlopen(request, timeout=self.timeout) as response:
                return response.status == 200
        except (OSError, URLError):
            return False

    def chat(self, prompt: str) -> str | None:
        payload = {
            "model": self.chat_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        result = self._post("/api/chat", payload)
        if not result:
            return None
        message = result.get("message")
        return message.get("content") if isinstance(message, dict) else None

    def embed(self, text: str) -> list[float] | None:
        # Ollama has used both /api/embeddings and /api/embed across releases.
        for endpoint, payload in (
            ("/api/embed", {"model": self.embed_model, "input": text}),
            ("/api/embeddings", {"model": self.embed_model, "prompt": text}),
        ):
            result = self._post(endpoint, payload)
            if not result:
                continue
            if isinstance(result.get("embeddings"), list) and result["embeddings"]:
                return result["embeddings"][0]
            if isinstance(result.get("embedding"), list):
                return result["embedding"]
        return None

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        request = Request(
            f"{self.base_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                value = json.loads(response.read().decode("utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, URLError, ValueError):
            return None
