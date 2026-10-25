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


class SignalEventType(StrEnum):
    FUNDING_ROUND = "funding_round"
    EXECUTIVE_CHANGE = "executive_change"
    LAYOFFS = "layoffs"
    TECH_STACK_CHANGE = "tech_stack_change"
    COMPETITOR_MENTION = "competitor_mention"
    EXPANSION = "expansion"


class SignalStatus(StrEnum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
