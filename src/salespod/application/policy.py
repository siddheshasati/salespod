from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ActionKind(StrEnum):
    CRM_READ = "crm_read"
    CRM_NOTE = "crm_note"
    STAGE_UPDATE = "stage_update"
    DISCOUNT = "discount"
    EXECUTIVE_OUTREACH = "executive_outreach"
    CONTRACT_CHANGE = "contract_change"


class PolicyOutcome(StrEnum):
    AUTO_APPROVED = "auto_approved"
    REQUIRES_APPROVAL = "requires_approval"
    DENIED = "denied"


@dataclass(frozen=True)
class PolicyDecision:
    action: ActionKind
    outcome: PolicyOutcome
    reason: str
    threshold: str | None = None


class PolicyEngine:
    """Centralize action safety rules before actions reach CRM or messaging."""

    def evaluate(
        self,
        action: ActionKind,
        *,
        discount_percent: float | None = None,
        executive_outreach: bool = False,
    ) -> PolicyDecision:
        if action in {ActionKind.CRM_READ, ActionKind.CRM_NOTE, ActionKind.STAGE_UPDATE}:
            return PolicyDecision(
                action=action,
                outcome=PolicyOutcome.AUTO_APPROVED,
                reason="Low-risk internal CRM action.",
            )
        if action is ActionKind.DISCOUNT:
            if discount_percent is None:
                return PolicyDecision(
                    action=action,
                    outcome=PolicyOutcome.REQUIRES_APPROVAL,
                    reason="A discount action requires an explicit percentage and manager review.",
                    threshold="15%",
                )
            if discount_percent > 15:
                return PolicyDecision(
                    action=action,
                    outcome=PolicyOutcome.REQUIRES_APPROVAL,
                    reason="Discounts above 15% require manager approval.",
                    threshold="15%",
                )
            return PolicyDecision(
                action=action,
                outcome=PolicyOutcome.AUTO_APPROVED,
                reason="Discount is within the 15% auto-approval threshold.",
                threshold="15%",
            )
        if action is ActionKind.EXECUTIVE_OUTREACH or executive_outreach:
            return PolicyDecision(
                action=action,
                outcome=PolicyOutcome.REQUIRES_APPROVAL,
                reason="Executive outreach requires human approval before sending.",
            )
        if action is ActionKind.CONTRACT_CHANGE:
            return PolicyDecision(
                action=action,
                outcome=PolicyOutcome.REQUIRES_APPROVAL,
                reason="Contract changes require human approval before execution.",
            )
        return PolicyDecision(
            action=action,
            outcome=PolicyOutcome.DENIED,
            reason="The requested action is not in the approved policy catalog.",
        )
