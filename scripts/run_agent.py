from __future__ import annotations

import argparse

from salespod.agents.graph import build_graph
from salespod.agents.model_provider import OllamaProvider
from salespod.application.crm_service import CrmService
from salespod.config import Settings
from salespod.infrastructure.db.session import create_session_factory


def main() -> None:
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(
        description="Run a manager request through the Sales Pod graph"
    )
    parser.add_argument("request", nargs="+", help="manager request")
    parser.add_argument("--actor", default="manager")
    parser.add_argument("--ollama", action="store_true", help="use qwen2.5:3b for response wording")
    args = parser.parse_args()
    service = CrmService(create_session_factory(settings.database_url))
    provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        chat_model=settings.ollama_chat_model,
        embed_model=settings.ollama_embed_model,
    )
    graph = build_graph(service, provider=provider, use_ollama=args.ollama)
    result = graph.invoke({"request": " ".join(args.request), "actor": args.actor})
    print(result.get("response", "No response was produced."))
    if result.get("errors"):
        print(f"Errors: {result['errors']}")


if __name__ == "__main__":
    main()
