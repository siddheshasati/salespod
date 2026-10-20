from __future__ import annotations

from enum import StrEnum


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    CONVERTED = "converted"


class DealStage(StrEnum):
    DISCOVERY = "discovery"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class ActivityType(StrEnum):
    NOTE = "note"
    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    STAGE_CHANGE = "stage_change"
    SYSTEM = "system"
