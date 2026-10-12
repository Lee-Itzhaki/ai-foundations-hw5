"""Shared Pydantic models passed between the Campus Customs agents.

Everything an agent hands to another agent (delegation requests, results,
proposed actions, approval state, errors) and everything written to the audit
trail is one of these models, so the hand-offs stay structured and checkable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------

class AgentName(str, Enum):
    BOSS = "boss"
    INVENTORY = "inventory"
    ACCOUNTING = "accounting"
    FACILITIES = "facilities"
    CUSTOMER_SERVICE = "customer_service"


class ActionStatus(str, Enum):
    """Lifecycle of a business action. Agents may only produce PROPOSED or
    BLOCKED (or FAILED); APPROVED requires a human and EXECUTED requires the
    approved action to have actually run through MCP."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    EXECUTED = "executed"
    BLOCKED = "blocked"
    FAILED = "failed"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING_HUMAN = "pending_human_approval"
    APPROVED = "approved"
    DENIED = "denied"


class ResultStatus(str, Enum):
    """Outcome of a unit of delegated work."""
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    NEEDS_HUMAN_APPROVAL = "needs_human_approval"
    BLOCKED = "blocked"
    FAILED = "failed"


class ErrorCode(str, Enum):
    MISSING_DATA = "missing_data"
    RECORD_NOT_FOUND = "record_not_found"
    OUT_OF_SCOPE = "out_of_scope"
    RULE_VIOLATION = "rule_violation"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    VENDOR_BLOCKED = "vendor_blocked"
    APPROVAL_REQUIRED = "approval_required"
    DELEGATION_LIMIT = "delegation_limit"
    STEP_LIMIT = "step_limit"
    USAGE_LIMIT = "usage_limit"
    TOOL_FAILURE = "tool_failure"
    REPEATED_FAILURES = "repeated_failures"
    MODEL_ERROR = "model_error"


# --------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------

class ErrorInfo(BaseModel):
    code: ErrorCode
    message: str
    recoverable: bool = False


class Evidence(BaseModel):
    """A database fact the agent relied on. `mcp_tool` must name an MCP tool
    that was actually called in this run; the output validator enforces it."""
    mcp_tool: str = Field(description="MCP tool that returned this fact")
    fact: str = Field(description="The fact, quoting returned field values exactly")


class PaymentProposal(BaseModel):
    """A payment the Accounting Agent has prepared but NOT executed. Must match
    a `check_payment_feasibility` result from this run."""
    payment_kind: Literal["vendor_invoice", "lease_rent"]
    reference_id: int = Field(description="invoices.id or leases.id")
    account_name: str
    amount: float = Field(description="Amount exactly as returned by check_payment_feasibility")
    payee: str
    balance_after_payment: float
    status: Literal[ActionStatus.PROPOSED, ActionStatus.BLOCKED] = ActionStatus.PROPOSED
    approval_status: ApprovalStatus = ApprovalStatus.PENDING_HUMAN
    blockers: list[str] = Field(default_factory=list)


class CustomerDraft(BaseModel):
    """An internal draft of a customer message. Never sent by any agent."""
    ticket_id: int
    recipient: str
    subject: str
    body: str
    status: Literal[ActionStatus.PROPOSED] = ActionStatus.PROPOSED
    sent: Literal[False] = False


class ProposedAction(BaseModel):
    """Any other recommended action (restock, quote, facilities task...)."""
    action_type: Literal["restock_order", "price_quote", "facilities_task",
                         "ticket_update", "other"]
    description: str
    status: Literal[ActionStatus.PROPOSED, ActionStatus.BLOCKED] = ActionStatus.PROPOSED
    approval_status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    blockers: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Delegation
# --------------------------------------------------------------------------

class DelegationRequest(BaseModel):
    """What an agent asks another agent to do. Source agent and depth are
    filled in by the orchestration code, not by the model."""
    target_agent: AgentName
    ticket_id: int | None = None
    task: str = Field(description="Specific question or job for the target agent")
    known_facts: list[str] = Field(
        default_factory=list,
        description="Facts already obtained from MCP tools, with the tool name, "
                    "so the target does not need to re-fetch them",
    )


class DelegationRecord(BaseModel):
    source: AgentName
    target: AgentName
    depth: int
    task: str
    result_status: ResultStatus


class AgentResult(BaseModel):
    """Structured result every specialist returns to whoever delegated to it."""
    agent: AgentName
    ticket_id: int | None = None
    status: ResultStatus
    summary: str
    evidence: list[Evidence] = Field(default_factory=list)
    payment_proposals: list[PaymentProposal] = Field(default_factory=list)
    customer_drafts: list[CustomerDraft] = Field(default_factory=list)
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    delegations: list[DelegationRecord] = Field(default_factory=list)
    errors: list[ErrorInfo] = Field(default_factory=list)
    return_to_boss_reason: str | None = Field(
        default=None,
        description="Why this work is being handed back (done, out of scope, blocked, needs approval)",
    )


# --------------------------------------------------------------------------
# Boss output
# --------------------------------------------------------------------------

class TicketOutcome(BaseModel):
    ticket_id: int
    ticket_type: str
    status: ResultStatus
    summary: str
    evidence: list[Evidence] = Field(default_factory=list)
    specialist_results: list[AgentResult] = Field(default_factory=list)
    payment_proposals: list[PaymentProposal] = Field(default_factory=list)
    customer_drafts: list[CustomerDraft] = Field(default_factory=list)
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    human_decisions_needed: list[str] = Field(default_factory=list)


class BossReport(BaseModel):
    shop_date: str | None = Field(description="desk.date_today as returned by get_shop_date")
    tickets: list[TicketOutcome]
    stop_reason: str


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------

class AuditEvent(str, Enum):
    RUN_STARTED = "run_started"
    AGENT_STARTED = "agent_started"
    AGENT_FINISHED = "agent_finished"
    MCP_TOOL_CALL = "mcp_tool_call"
    DELEGATION = "delegation"
    DELEGATION_REFUSED = "delegation_refused"
    OUTPUT_REJECTED = "output_rejected"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECISION = "approval_decision"
    LIMIT_REACHED = "limit_reached"
    ERROR = "error"
    RUN_FINISHED = "run_finished"
    API_REQUEST = "api_request"
    DATABASE_RESET = "database_reset"


class AuditEntry(BaseModel):
    """One line of the operational record. No secrets, no hidden reasoning."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    run_id: str
    step: int
    event: AuditEvent
    agent: AgentName | None = None
    ticket_id: int | None = None
    action: str | None = None
    delegation_source: AgentName | None = None
    delegation_target: AgentName | None = None
    delegation_depth: int | None = None
    mcp_tool: str | None = None
    tool_args: dict[str, Any] | None = None
    result_summary: str | None = None
    approval_status: ApprovalStatus | None = None
    outcome: str | None = None
    error: str | None = None
    stop_or_continue: str | None = None
