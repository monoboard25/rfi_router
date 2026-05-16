"""Pydantic models for queue messages, webhook contracts, and orchestrator I/O.

Shared between validator (producer) and approvals (consumer). Keep this
file in lockstep with the matching producer-side schema in the validator
repo to prevent drift between enqueue and dequeue.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


Tier = Literal["low", "high"]
Decision = Literal["approved", "denied"]
Channel = Literal["telegram-dm", "dashboard-magic-link", "kill-switch-queue", "email-timeout"]


class EscalationQueueMessage(BaseModel):
    """Message enqueued by validator chain to escalation-events queue.

    Payload itself is stored separately in Blob (referenced by blob_url)
    because Storage Queue messages cap at 64KB and agent payloads
    (Daily Report, Bid Assist) can exceed that.
    """

    run_id: str
    partition_key: str = Field(description="Azure Table PartitionKey == agent_id")
    agent_id: str
    tier: Tier
    blob_url: str = Field(description="Full URL to payload JSON in Blob Storage")
    matrix_rule_id: str
    escalation_reason: str
    constitution_version: str
    enqueued_at: datetime


class AgentPayload(BaseModel):
    """Full agent output, fetched from Blob by orchestrator."""

    run_id: str
    agent_id: str
    output: dict
    writes_proposed: list = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    """Posted to validator approval webhook on operator decision."""

    run_id: str
    partition_key: str
    decision: Decision
    operator_id: str = Field(description="Entra ID OID of approver")
    operator_channel: Channel
    decision_timestamp: datetime
    constitution_version: str


class TelegramCallbackData(BaseModel):
    """Decoded callback_query.data from Telegram inline button tap.

    Format: <action>:<run_id>  e.g.  approve:1762...3
    """

    action: Decision
    run_id: str

    @classmethod
    def parse(cls, raw: str) -> "TelegramCallbackData":
        action, run_id = raw.split(":", 1)
        if action not in ("approved", "denied"):
            # Tolerate short forms from button payloads
            if action == "approve":
                action = "approved"
            elif action == "deny":
                action = "denied"
            else:
                raise ValueError(f"Unknown callback action: {action!r}")
        return cls(action=action, run_id=run_id)  # type: ignore[arg-type]


class OperatorDecisionEvent(BaseModel):
    """Payload of `RaiseEvent` from telegram_callback to orchestrator."""

    decision: Decision
    operator_id: str
    operator_channel: Channel
    decision_timestamp: datetime
