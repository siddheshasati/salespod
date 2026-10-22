from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from salespod.domain.enums import ActivityType, DealStage

UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


@dataclass(frozen=True)
class Route:
    intent: str
    tool_name: str | None
    tool_args: dict[str, Any]
    error: str | None = None


def route_request(request: str, *, actor: str = "manager") -> Route:
    """Route common manager requests without trusting an LLM to invent writes."""
    text = " ".join(request.strip().split())
    lower = text.lower()
    ids = [UUID(match) for match in UUID_PATTERN.findall(text)]

    if any(
        token in lower for token in ("pipeline snapshot", "pipeline forecast", "current pipeline")
    ):
        return Route("pipeline_snapshot", "get_pipeline_snapshot", {})

    stage_match = re.search(
        r"(?:update|move|advance)\s+(?:deal\s+)?(?:stage\s+)?(?:of\s+)?(?:[0-9a-f-]{36}\s+)?to\s+(discovery|qualification|proposal|negotiation|closed_won|closed_lost)",
        lower,
    )
    if any(token in lower for token in ("update stage", "move deal", "advance deal")):
        if not ids:
            return Route(
                "update_stage",
                None,
                {},
                "An explicit deal UUID is required for a stage update.",
            )
        if not stage_match:
            return Route("update_stage", None, {}, "A target stage is required for a stage update.")
        version_match = re.search(r"(?:version|v)\s*[=:]?\s*(\d+)", lower)
        if not version_match:
            return Route(
                "update_stage",
                None,
                {},
                "An expected version is required to prevent a lost update.",
            )
        return Route(
            "update_stage",
            "update_stage",
            {
                "deal_id": ids[0],
                "new_stage": DealStage(stage_match.group(1)),
                "reason": text,
                "actor": actor,
                "expected_version": int(version_match.group(1)),
                "idempotency_key": f"manager:{hashlib.sha256(text.encode()).hexdigest()}",
            },
        )

    if any(token in lower for token in ("log activity", "record activity", "log a note")):
        if not ids:
            return Route("log_activity", None, {}, "An entity UUID is required to log an activity.")
        return Route(
            "log_activity",
            "log_activity",
            {
                "activity_type": ActivityType.NOTE,
                "body": text,
                "actor": actor,
                "deal_id": ids[0],
                "idempotency_key": f"manager-note:{hashlib.sha256(text.encode()).hexdigest()}",
            },
        )

    if any(token in lower for token in ("get deal", "show deal", "deal details")):
        if not ids:
            return Route("get_deal", None, {}, "A deal UUID is required.")
        return Route("get_deal", "get_deal", {"deal_id": ids[0]})

    if any(token in lower for token in ("search lead", "find lead", "show lead")):
        query = re.sub(
            r".*?(?:search|find|show)\s+leads?\s*(?:for|at|named)?\s*", "", text, flags=re.I
        )
        return Route("search_leads", "search_leads", {"query": query or None, "limit": 20})

    return Route(
        "unsupported",
        None,
        {},
        "The supervisor could not map this request to a safe CRM operation.",
    )
