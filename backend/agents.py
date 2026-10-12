"""The five Campus Customs agents and the code that bounds them.

- Every agent uses the same model (gpt-6-luna via Portkey, see config.py).
- Every database fact comes from the campus-customs MCP server. Each agent
  sees only an allow-listed subset of MCP tools; `execute_approved_payment`
  is on no agent's list and is additionally refused by the call hook.
- Every agent has a `delegate_task` tool that can reach any other agent.
  Depth, total delegations, cycles, and total steps are capped in code.
- Output validators reject results that cite facts from tools that were never
  called, payment proposals that don't match a feasibility check, or actions
  that claim approval/execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastmcp.client.transports import StdioTransport
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models import Model

from . import config
from .audit import AuditTrail, redact, summarize
from .models import (
    AgentName, AgentResult, ApprovalStatus, AuditEntry, AuditEvent, BossReport,
    CustomerDraft, DelegationRecord, DelegationRequest, ErrorCode, ErrorInfo,
    PaymentProposal, ResultStatus,
)

# --------------------------------------------------------------------------
# Least-privilege MCP tool access per agent
# --------------------------------------------------------------------------

COMMON_TOOLS = {"get_shop_date", "get_ticket_details"}

ALLOWED_TOOLS: dict[AgentName, frozenset[str]] = {
    AgentName.BOSS: frozenset(COMMON_TOOLS | {"list_open_tickets"}),
    AgentName.INVENTORY: frozenset(COMMON_TOOLS | {
        "get_inventory_stock_for_sku_size", "get_sku_cost_and_list_price",
        "list_vendors", "get_vendor_shipping_status",
    }),
    AgentName.ACCOUNTING: frozenset(COMMON_TOOLS | {
        "get_invoice_with_vendor", "get_lease_rent_and_cash_balance",
        "check_payment_feasibility", "list_cash_accounts",
    }),
    AgentName.FACILITIES: frozenset(COMMON_TOOLS | {"get_lease_rent_and_cash_balance", "list_cash_accounts"}),
    AgentName.CUSTOMER_SERVICE: frozenset(COMMON_TOOLS | {
        "get_inventory_stock_for_sku_size", "get_sku_cost_and_list_price",
    }),
}

# Never callable by an agent, regardless of the allow-list.
HUMAN_ONLY_TOOLS = frozenset({"execute_approved_payment", "resolve_ticket"})

PROMPT_FILES = {
    AgentName.BOSS: "boss.md",
    AgentName.INVENTORY: "inventory.md",
    AgentName.ACCOUNTING: "accounting.md",
    AgentName.FACILITIES: "facilities.md",
    AgentName.CUSTOMER_SERVICE: "customer_service.md",
}


# --------------------------------------------------------------------------
# Run state shared by every agent in one run
# --------------------------------------------------------------------------

@dataclass
class ToolCallRecord:
    agent: AgentName
    tool: str
    args: dict[str, Any]
    result: Any


@dataclass
class RunState:
    run_id: str
    audit: AuditTrail
    step: int = 0
    delegation_count: int = 0
    tool_failures: int = 0
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    delegation_records: list[tuple[AgentName, DelegationRecord]] = field(default_factory=list)
    customer_drafts: list[CustomerDraft] = field(default_factory=list)
    payment_proposals: list[PaymentProposal] = field(default_factory=list)

    def log(self, event: AuditEvent, **fields: Any) -> int:
        self.step += 1
        self.audit.append(AuditEntry(run_id=self.run_id, step=self.step, event=event, **fields))
        return self.step

    @property
    def steps_exhausted(self) -> bool:
        return self.step >= config.MAX_STEPS_PER_RUN

    def tools_called(self) -> set[str]:
        return {c.tool for c in self.tool_calls}


@dataclass
class AgentDeps:
    state: RunState
    agent: AgentName
    ticket_id: int | None
    depth: int
    chain: tuple[AgentName, ...]


# --------------------------------------------------------------------------
# MCP connection with audited, access-checked tool calls
# --------------------------------------------------------------------------

def _is_failure(result: Any) -> bool:
    if isinstance(result, dict):
        if result.get("found") is False or result.get("status") == "failed":
            return True
        if isinstance(result.get("lease"), dict) and result["lease"].get("found") is False:
            return True
        if isinstance(result.get("cash_account"), dict) and result["cash_account"].get("found") is False:
            return True
    return False


async def _audited_tool_call(ctx: RunContext[AgentDeps], call_tool, name: str, args: dict[str, Any]):
    deps, state = ctx.deps, ctx.deps.state
    base = dict(agent=deps.agent, ticket_id=deps.ticket_id, mcp_tool=name, tool_args=redact(args))

    if name in HUMAN_ONLY_TOOLS or name not in ALLOWED_TOOLS[deps.agent]:
        state.log(AuditEvent.MCP_TOOL_CALL, **base, outcome="refused",
                  error=f"{deps.agent.value} is not permitted to call {name}",
                  stop_or_continue="continue")
        return {"status": "refused", "reason": f"Tool {name} is not available to the {deps.agent.value} agent."}
    if state.steps_exhausted:
        state.log(AuditEvent.LIMIT_REACHED, **base, outcome="refused",
                  error="step limit reached", stop_or_continue="stop")
        return {"status": "refused", "reason": "Run step limit reached. Stop and report what you have."}
    if state.tool_failures >= config.MAX_TOOL_FAILURES_PER_RUN:
        state.log(AuditEvent.LIMIT_REACHED, **base, outcome="refused",
                  error="repeated tool failures", stop_or_continue="stop")
        return {"status": "refused",
                "reason": "Too many failed or not-found lookups in this run. Stop and report missing data."}

    try:
        result = await call_tool(name, args)
    except Exception as exc:
        state.tool_failures += 1
        state.log(AuditEvent.MCP_TOOL_CALL, **base, outcome="failed", error=str(exc)[:300],
                  stop_or_continue="continue")
        return {"status": "failed", "error": str(exc)[:300]}

    failed = _is_failure(result)
    if failed:
        state.tool_failures += 1
    state.tool_calls.append(ToolCallRecord(deps.agent, name, dict(args), result))
    state.log(AuditEvent.MCP_TOOL_CALL, **base, result_summary=summarize(result),
              outcome="not_found_or_failed" if failed else "ok", stop_or_continue="continue")
    return result


def build_mcp_toolset() -> MCPToolset:
    transport = StdioTransport(
        command=config.MCP_PYTHON,
        args=[str(config.MCP_SERVER_SCRIPT)],
        cwd=str(config.PROJECT_ROOT),
    )
    return MCPToolset(transport, process_tool_call=_audited_tool_call,
                      tool_error_behavior="failed", max_retries=1)


# --------------------------------------------------------------------------
# Output validation (deterministic guards against invented facts / actions)
# --------------------------------------------------------------------------

def _feasibility_for(state: RunState, p: PaymentProposal) -> dict[str, Any] | None:
    for call in reversed(state.tool_calls):
        if (call.tool == "check_payment_feasibility"
                and call.args.get("payment_kind") == p.payment_kind
                and call.args.get("reference_id") == p.reference_id
                and call.args.get("account_name") == p.account_name):
            return call.result
    return None


def _validate_common(deps: AgentDeps, evidence, payments, drafts, actions) -> None:
    called = deps.state.tools_called()
    for ev in evidence:
        if ev.mcp_tool not in called:
            raise ModelRetry(f"Evidence cites MCP tool '{ev.mcp_tool}', which was not called in this run. "
                             "Only cite facts returned by MCP tools you (or a specialist) actually called.")
    for p in payments:
        fz = _feasibility_for(deps.state, p)
        if fz is None:
            raise ModelRetry(f"Payment proposal for {p.payment_kind} {p.reference_id} has no matching "
                             "check_payment_feasibility result. Run the check or drop the proposal.")
        ob = fz.get("obligation") or {}
        if ob.get("amount") != p.amount or fz.get("balance_after_payment") != p.balance_after_payment:
            raise ModelRetry("Payment proposal amount/balance must equal the check_payment_feasibility result exactly.")
        if fz.get("decision") == "blocked" and p.status != "blocked":
            raise ModelRetry("check_payment_feasibility returned 'blocked'; the proposal status must be 'blocked'.")
        if p.approval_status != ApprovalStatus.PENDING_HUMAN:
            raise ModelRetry("Agents cannot approve or deny payments; approval_status must be pending_human_approval.")
    for a in actions:
        if a.approval_status in (ApprovalStatus.APPROVED, ApprovalStatus.DENIED):
            raise ModelRetry("Agents cannot record a human approval decision.")
    if drafts and deps.agent not in (AgentName.CUSTOMER_SERVICE, AgentName.BOSS):
        raise ModelRetry("Only the Customer Service Agent drafts customer messages; delegate to it.")
    if deps.agent == AgentName.BOSS:
        known = {(d.ticket_id, d.subject) for d in deps.state.customer_drafts}
        if any((d.ticket_id, d.subject) not in known for d in drafts):
            raise ModelRetry("Boss may only pass along customer drafts produced by the Customer Service Agent.")
    if payments and deps.agent not in (AgentName.ACCOUNTING, AgentName.BOSS):
        raise ModelRetry("Only the Accounting Agent prepares payment proposals; delegate to it.")


async def _validate_agent_result(ctx: RunContext[AgentDeps], out: AgentResult) -> AgentResult:
    deps = ctx.deps
    out.agent = deps.agent
    _validate_common(deps, out.evidence, out.payment_proposals, out.customer_drafts, out.proposed_actions)
    # Delegation history is filled from the run record, not from the model.
    out.delegations = [r for src, r in deps.state.delegation_records
                       if src == deps.agent and r.depth == deps.depth + 1]
    return out


async def _validate_boss_report(ctx: RunContext[AgentDeps], out: BossReport) -> BossReport:
    deps = ctx.deps
    for t in out.tickets:
        _validate_common(deps, t.evidence, t.payment_proposals, t.customer_drafts, t.proposed_actions)
    return out


# --------------------------------------------------------------------------
# Delegation
# --------------------------------------------------------------------------

def _failed(agent: AgentName, ticket_id: int | None, code: ErrorCode, msg: str,
            status: ResultStatus = ResultStatus.FAILED) -> AgentResult:
    return AgentResult(agent=agent, ticket_id=ticket_id, status=status, summary=msg,
                       errors=[ErrorInfo(code=code, message=msg)], return_to_boss_reason=msg)


def _make_delegate_tool(registry: dict[AgentName, Agent]):
    async def delegate_task(ctx: RunContext[AgentDeps], request: DelegationRequest) -> AgentResult:
        """Hand a specific task to another Campus Customs agent and get its structured result.

        Use this when the work belongs to another agent's scope. Limits on
        depth, total delegations, cycles, and steps are enforced by the system;
        if a delegation is refused, report that instead of retrying it.
        """
        deps, state = ctx.deps, ctx.deps.state
        src, tgt = deps.agent, request.target_agent
        ticket_id = request.ticket_id if request.ticket_id is not None else deps.ticket_id
        depth = deps.depth + 1

        refusal = None
        if tgt == src:
            refusal = (ErrorCode.OUT_OF_SCOPE, "An agent cannot delegate to itself.")
        elif tgt in deps.chain:
            refusal = (ErrorCode.DELEGATION_LIMIT,
                       f"{tgt.value} is already in this delegation chain; return the work instead of looping.")
        elif depth > config.MAX_DELEGATION_DEPTH:
            refusal = (ErrorCode.DELEGATION_LIMIT, f"Maximum delegation depth {config.MAX_DELEGATION_DEPTH} reached.")
        elif state.delegation_count >= config.MAX_DELEGATIONS_PER_RUN:
            refusal = (ErrorCode.DELEGATION_LIMIT,
                       f"Maximum of {config.MAX_DELEGATIONS_PER_RUN} delegations per run reached.")
        elif state.steps_exhausted:
            refusal = (ErrorCode.STEP_LIMIT, "Run step limit reached.")
        if refusal:
            state.log(AuditEvent.DELEGATION_REFUSED, agent=src, ticket_id=ticket_id, action=request.task,
                      delegation_source=src, delegation_target=tgt, delegation_depth=depth,
                      outcome="refused", error=refusal[1], stop_or_continue="return to caller")
            return _failed(tgt, ticket_id, refusal[0], refusal[1], ResultStatus.BLOCKED)

        state.delegation_count += 1
        state.log(AuditEvent.DELEGATION, agent=src, ticket_id=ticket_id, action=request.task,
                  delegation_source=src, delegation_target=tgt, delegation_depth=depth,
                  outcome="started", stop_or_continue="continue")

        child = AgentDeps(state=state, agent=tgt, ticket_id=ticket_id, depth=depth, chain=deps.chain + (tgt,))
        facts = "\n".join(f"- {f}" for f in request.known_facts) or "- (none provided)"
        prompt = (f"Delegated by the {src.value} agent (delegation depth {depth}).\n"
                  f"Ticket: {ticket_id}\nTask: {request.task}\n"
                  f"Facts already obtained from MCP tools:\n{facts}")
        try:
            run = await registry[tgt].run(prompt, deps=child, usage=ctx.usage,
                                          usage_limits=config.RUN_USAGE_LIMITS)
            out = run.output
            if isinstance(out, BossReport):  # boss reached from a specialist-rooted run
                out = AgentResult(agent=tgt, ticket_id=ticket_id, status=ResultStatus.PARTIAL,
                                  summary=out.stop_reason)
        except UsageLimitExceeded as exc:
            out = _failed(tgt, ticket_id, ErrorCode.USAGE_LIMIT, f"Usage limit reached: {exc}")
        except Exception as exc:
            out = _failed(tgt, ticket_id, ErrorCode.MODEL_ERROR, f"{type(exc).__name__}: {str(exc)[:200]}")

        state.customer_drafts.extend(out.customer_drafts)
        state.payment_proposals.extend(out.payment_proposals)
        state.delegation_records.append(
            (src, DelegationRecord(source=src, target=tgt, depth=depth, task=request.task, result_status=out.status)))
        pending = any(p.status == "proposed" for p in out.payment_proposals)
        state.log(AuditEvent.DELEGATION, agent=tgt, ticket_id=ticket_id, action=request.task,
                  delegation_source=tgt, delegation_target=src, delegation_depth=depth,
                  result_summary=summarize(out.summary), outcome=out.status.value,
                  approval_status=ApprovalStatus.PENDING_HUMAN if pending else None,
                  error="; ".join(e.message for e in out.errors) or None,
                  stop_or_continue="returned to caller")
        return out

    return delegate_task


# --------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------

def load_prompt(agent: AgentName) -> str:
    return (config.PROMPTS_DIR / PROMPT_FILES[agent]).read_text()


def _runtime_context(ctx: RunContext[AgentDeps]) -> str:
    d = ctx.deps
    s = d.state
    return (f"Runtime context: you are the {d.agent.value} agent; run {s.run_id}; "
            f"delegation depth {d.depth} of max {config.MAX_DELEGATION_DEPTH}; "
            f"delegations used {s.delegation_count}/{config.MAX_DELEGATIONS_PER_RUN}; "
            f"steps used {s.step}/{config.MAX_STEPS_PER_RUN}; "
            f"current ticket: {d.ticket_id}. "
            f"MCP tools available to you: {', '.join(sorted(ALLOWED_TOOLS[d.agent]))}.")


def build_agents(model: Model, mcp_toolset: MCPToolset) -> dict[AgentName, Agent]:
    registry: dict[AgentName, Agent] = {}
    delegate_task = _make_delegate_tool(registry)

    for name in AgentName:
        allowed = ALLOWED_TOOLS[name]
        toolset = mcp_toolset.filtered(lambda ctx, td, allowed=allowed: td.name in allowed)
        is_boss = name == AgentName.BOSS
        agent = Agent(
            model,
            name=f"{name.value}_agent",
            instructions=[load_prompt(name), _runtime_context],
            deps_type=AgentDeps,
            output_type=BossReport if is_boss else AgentResult,
            toolsets=[toolset],
            retries=config.AGENT_RETRIES,
        )
        agent.tool(delegate_task)
        agent.output_validator(_validate_boss_report if is_boss else _validate_agent_result)
        registry[name] = agent
    return registry
