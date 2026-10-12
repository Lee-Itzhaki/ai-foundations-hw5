"""Run the agent team and, separately, execute human-approved actions.

`run_tickets` starts the Boss Agent, which coordinates specialists through
bounded delegation. It never executes anything: payment and purchase
proposals are registered in the ActionStore as `pending_human_approval`.

`approve_action` is the only path that executes a prepared payment. It
requires an explicit human approval, re-validates the action and the cash
balance through MCP, and calls the MCP server's `execute_approved_payment`,
which re-checks every rule inside one database transaction.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from pydantic_ai.exceptions import UsageLimitExceeded

from . import config
from .actions import ActionStore, PreparedAction
from .agents import AgentDeps, RunState, build_agents, build_mcp_toolset
from .audit import AuditTrail, summarize
from .mcp_client import MCPGateway
from .models import (
    ActionStatus, AgentName, ApprovalStatus, AuditEvent, BossReport, ResultStatus,
)


@dataclass
class RunOutcome:
    run_id: str
    report: BossReport | None
    action_ids: list[str] = field(default_factory=list)
    error: str | None = None


def _boss_prompt(ticket_ids: list[int] | None) -> str:
    scope = (f"Work only on tickets {', '.join(map(str, ticket_ids))}."
             if ticket_ids else "Work on every open ticket.")
    return (f"{scope} Analyze each ticket, delegate to the right specialists, and "
            "return a BossReport. Do not execute payments, send messages, or change "
            "any records; anything that needs a human must be reported as pending.")


def _register_actions(state: RunState, report: BossReport, store: ActionStore) -> list[str]:
    """Register validated payment proposals and restock proposals for human review."""
    ids: list[str] = []
    ticket_for = {(p.payment_kind, p.reference_id): t.ticket_id
                  for t in report.tickets for p in t.payment_proposals}
    single = report.tickets[0].ticket_id if len(report.tickets) == 1 else None
    for p in state.payment_proposals:  # already validated against check_payment_feasibility
        if p.status != ActionStatus.PROPOSED:
            continue
        a = store.add(PreparedAction(
            kind="payment", run_id=state.run_id,
            ticket_id=ticket_for.get((p.payment_kind, p.reference_id), single),
            prepared_by=AgentName.ACCOUNTING.value,
            description=f"Pay {p.payment_kind} {p.reference_id} to {p.payee} from {p.account_name}",
            payment_kind=p.payment_kind, reference_id=p.reference_id,
            account_name=p.account_name, amount=p.amount, payee=p.payee,
            balance_after_at_preparation=p.balance_after_payment))
        ids.append(a.action_id)
    for t in report.tickets:
        for pa in t.proposed_actions:
            if pa.action_type == "restock_order" and pa.status == ActionStatus.PROPOSED:
                a = store.add(PreparedAction(kind="purchase", run_id=state.run_id, ticket_id=t.ticket_id,
                                             prepared_by=AgentName.INVENTORY.value,
                                             description=pa.description, blockers=pa.blockers))
                ids.append(a.action_id)
    # A ticket the Boss reports fully complete gets a resolution request for a human.
    for t in report.tickets:
        if t.status == ResultStatus.SUCCEEDED and not t.blockers and not t.human_decisions_needed:
            a = store.add(PreparedAction(kind="ticket_resolution", run_id=state.run_id, ticket_id=t.ticket_id,
                                         prepared_by=AgentName.BOSS.value,
                                         description=f"Mark ticket {t.ticket_id} resolved: {t.summary}"[:500]))
            ids.append(a.action_id)
    for action_id in dict.fromkeys(ids):
        a = store.get(action_id)
        state.log(AuditEvent.APPROVAL_REQUESTED, agent=AgentName(a.prepared_by), ticket_id=a.ticket_id,
                  action=f"{a.action_id}: {a.description}", approval_status=ApprovalStatus.PENDING_HUMAN,
                  result_summary=summarize({"amount": a.amount, "kind": a.kind}),
                  outcome="pending_human_approval", stop_or_continue="waiting for human")
    return list(dict.fromkeys(ids))


async def run_tickets(ticket_ids: list[int] | None = None, *, run_id: str | None = None,
                      audit: AuditTrail | None = None, store: ActionStore | None = None) -> RunOutcome:
    state = RunState(run_id=run_id or uuid.uuid4().hex[:12], audit=audit or AuditTrail())
    focus = ticket_ids[0] if ticket_ids and len(ticket_ids) == 1 else None
    state.log(AuditEvent.RUN_STARTED, agent=AgentName.BOSS, ticket_id=focus,
              action=f"analyze tickets {ticket_ids or 'all open'}", stop_or_continue="continue")

    mcp = build_mcp_toolset()
    agents = build_agents(config.build_model(), mcp)
    deps = AgentDeps(state=state, agent=AgentName.BOSS, ticket_id=focus, depth=0,
                     chain=(AgentName.BOSS,))
    try:
        async with mcp:
            run = await agents[AgentName.BOSS].run(
                _boss_prompt(ticket_ids), deps=deps, usage_limits=config.RUN_USAGE_LIMITS)
        report: BossReport = run.output
        for t in report.tickets:
            state.log(AuditEvent.AGENT_FINISHED, agent=AgentName.BOSS, ticket_id=t.ticket_id,
                      action="ticket outcome", result_summary=summarize(t.summary),
                      outcome=t.status.value,
                      approval_status=ApprovalStatus.PENDING_HUMAN if t.human_decisions_needed else None,
                      stop_or_continue="; ".join(t.blockers)[:300] or None)
        action_ids = _register_actions(state, report, store or ActionStore())
        state.log(AuditEvent.RUN_FINISHED, agent=AgentName.BOSS, ticket_id=focus, outcome="completed",
                  result_summary=summarize([(t.ticket_id, t.status.value) for t in report.tickets]),
                  stop_or_continue=report.stop_reason)
        return RunOutcome(state.run_id, report, action_ids)
    except UsageLimitExceeded as exc:
        state.log(AuditEvent.LIMIT_REACHED, agent=AgentName.BOSS, ticket_id=focus, outcome="stopped",
                  error=str(exc), stop_or_continue="stop: usage limit")
        return RunOutcome(state.run_id, None, error=f"Usage limit reached: {exc}")
    except Exception as exc:
        msg = f"{type(exc).__name__}: {str(exc)[:300]}"
        state.log(AuditEvent.ERROR, agent=AgentName.BOSS, ticket_id=focus, outcome="failed",
                  error=msg, stop_or_continue="stop: error")
        return RunOutcome(state.run_id, None, error=msg)


# --------------------------------------------------------------------------
# Human approval
# --------------------------------------------------------------------------

class ApprovalError(Exception):
    def __init__(self, status_code: int, code: str, message: str, action: PreparedAction | None = None):
        super().__init__(message)
        self.status_code, self.code, self.message, self.action = status_code, code, message, action


_approval_lock = asyncio.Lock()


async def approve_action(action_id: str, approved_by: str, gateway: MCPGateway,
                         store: ActionStore | None = None,
                         audit: AuditTrail | None = None) -> tuple[PreparedAction, float | None]:
    """Execute (payment) or record approval of (purchase) one prepared action.

    Raises ApprovalError with an HTTP-style status for every refusal.
    """
    store = store or ActionStore()
    state = RunState(run_id="approval_" + uuid.uuid4().hex[:8], audit=audit or AuditTrail())
    approver = approved_by.strip()

    def log(outcome: str, approval: ApprovalStatus, a: PreparedAction | None, **kw):
        state.log(AuditEvent.APPROVAL_DECISION, ticket_id=a.ticket_id if a else None,
                  action=f"approve {action_id}", approval_status=approval, outcome=outcome, **kw)

    async with _approval_lock:
        action = store.get(action_id)
        if action is None:
            log("not_found", ApprovalStatus.DENIED, None, error="unknown action", stop_or_continue="stop")
            raise ApprovalError(404, "action_not_found", f"No prepared action with id {action_id}.")
        if action.status != "pending_human_approval":
            log("refused", ApprovalStatus.DENIED, action, error=f"action is {action.status}",
                stop_or_continue="stop: not pending")
            raise ApprovalError(409, f"action_{action.status}",
                                f"Action {action_id} is '{action.status}', not pending; it will not run again.",
                                action)

        if action.kind == "ticket_resolution":
            claimed = store.transition(action_id, "pending_human_approval", "executing", approved_by=approver)
            if claimed is None:
                raise ApprovalError(409, "action_not_pending", f"Action {action_id} is no longer pending.")
            args = {"ticket_id": action.ticket_id, "approved_by": approver}
            result = await gateway.call("resolve_ticket", args)
            state.log(AuditEvent.MCP_TOOL_CALL, ticket_id=action.ticket_id, mcp_tool="resolve_ticket",
                      tool_args=args, result_summary=summarize(result), approval_status=ApprovalStatus.APPROVED,
                      outcome=result.get("status"), stop_or_continue="stop")
            if result.get("status") == "executed":
                done = store.transition(action_id, "executing", "executed")
                log("executed", ApprovalStatus.APPROVED, done, stop_or_continue="stop: ticket resolved")
                return done, None
            blockers = result.get("blockers") or [result.get("error", "resolution refused")]
            refused = store.transition(action_id, "executing", "blocked", blockers=blockers)
            log("blocked", ApprovalStatus.APPROVED, refused, error="; ".join(blockers), stop_or_continue="stop")
            raise ApprovalError(409, "action_blocked", "; ".join(blockers), refused)

        if action.kind == "purchase":
            # No system executor: placing an order means contacting a vendor, which only a human may do.
            done = store.transition(action_id, "pending_human_approval", "approved", approved_by=approver,
                                    note="Approved by a human; the order must be placed by a human. "
                                         "No vendor was contacted by the system.")
            log("approved_not_executed", ApprovalStatus.APPROVED, done, stop_or_continue="stop")
            return done, None

        # ---- payment: revalidate against the database through MCP ----
        args = dict(payment_kind=action.payment_kind, reference_id=action.reference_id,
                    account_name=action.account_name)
        check = await gateway.call("check_payment_feasibility", args)
        current = (check.get("obligation") or {}).get("amount")
        if current is None or round(current, 2) != round(action.amount or 0, 2):
            store.transition(action_id, "pending_human_approval", "stale",
                             blockers=[f"Prepared amount {action.amount} no longer matches database amount {current}."])
            log("stale", ApprovalStatus.DENIED, action, tool_args=args, mcp_tool="check_payment_feasibility",
                result_summary=summarize(check), stop_or_continue="stop: stale")
            raise ApprovalError(409, "action_stale",
                                f"Prepared amount {action.amount} does not match current amount {current}.",
                                store.get(action_id))
        if check.get("decision") != "ready_for_human_approval":
            blocked = store.transition(action_id, "pending_human_approval", "blocked", blockers=check.get("blockers", []))
            insufficient = any("Insufficient" in b for b in check.get("blockers", []))
            log("blocked", ApprovalStatus.DENIED, action, mcp_tool="check_payment_feasibility", tool_args=args,
                result_summary=summarize(check), error="; ".join(check.get("blockers", [])),
                stop_or_continue="stop: blocked")
            raise ApprovalError(409, "insufficient_funds" if insufficient else "action_blocked",
                                "; ".join(check.get("blockers", [])) or "Payment is blocked.", blocked)

        # Claim the action so it can never execute twice.
        claimed = store.transition(action_id, "pending_human_approval", "executing", approved_by=approver)
        if claimed is None:
            raise ApprovalError(409, "action_not_pending", f"Action {action_id} is no longer pending.")
        exec_args = {**args, "approved_by": approver, "expected_amount": action.amount}
        try:
            result = await gateway.call("execute_approved_payment", exec_args)
        except Exception as exc:
            store.transition(action_id, "executing", "failed", blockers=[str(exc)[:300]])
            log("failed", ApprovalStatus.APPROVED, action, mcp_tool="execute_approved_payment",
                tool_args=exec_args, error=str(exc)[:300], stop_or_continue="stop: error")
            raise
        state.log(AuditEvent.MCP_TOOL_CALL, ticket_id=action.ticket_id, mcp_tool="execute_approved_payment",
                  tool_args=exec_args, result_summary=summarize(result), approval_status=ApprovalStatus.APPROVED,
                  outcome=result.get("status"), stop_or_continue="stop")
        if result.get("status") == "executed":
            done = store.transition(action_id, "executing", "executed", payment_id=result.get("payment_id"),
                                    balance_after=result.get("balance_after_payment"))
            log("executed", ApprovalStatus.APPROVED, done, stop_or_continue="stop: done")
            return done, result.get("balance_after_payment")
        new = "failed" if result.get("status") == "failed" else "blocked"
        blockers = result.get("blockers") or [result.get("error", "execution refused")]
        refused = store.transition(action_id, "executing", new, blockers=blockers)
        insufficient = any("Insufficient" in b for b in blockers)
        log(new, ApprovalStatus.APPROVED, refused, error="; ".join(blockers), stop_or_continue="stop")
        raise ApprovalError(409, "insufficient_funds" if insufficient else f"action_{new}",
                            "; ".join(blockers), refused)
