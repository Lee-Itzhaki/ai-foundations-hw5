"""Campus Customs FastAPI backend for the React dashboard.

Run from the backend/ directory:

    uvicorn main:app --reload --port 8000

All shop data is read and written through the campus-customs MCP server
(the same one the agents use). This module adds HTTP routes, run tracking,
the human-approval endpoint, and the working-database reset.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import uuid
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

# Allow `uvicorn main:app` from backend/ to import the `backend` package.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, Query, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

from backend import config  # noqa: E402
from backend import orchestrator  # noqa: E402
from backend.actions import ActionStore, PreparedAction  # noqa: E402
from backend.agents import RunState  # noqa: E402
from backend.audit import AuditTrail, AuditTrailCorrupt  # noqa: E402
from backend.mcp_client import MCPCallError, MCPGateway  # noqa: E402
from backend.models import AuditEvent, BossReport  # noqa: E402

ORIGINAL_DB = config.PROJECT_ROOT / "data" / "campus_customs.db"
WORKING_DB = config.PROJECT_ROOT / "data" / "campus_customs_new.db"
CHECKING = "checking"

DEFAULT_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:3000", "http://127.0.0.1:3000"]
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()] \
    or DEFAULT_ORIGINS


# --------------------------------------------------------------------------
# API contracts
# --------------------------------------------------------------------------

class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        self.status_code, self.code, self.message, self.details = status_code, code, message, details


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    working_db_present: bool
    original_db_present: bool
    mcp_reachable: bool
    model_configured: bool = Field(description="True if PORTKEY_API_KEY is set (value never returned)")
    model: str
    shop_date: str | None = None


class Ticket(BaseModel):
    id: int
    type: str
    requester: str
    subject: str
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    lease_id: int | None = None
    invoice_id: int | None = None
    status: str
    is_open: bool
    notes: str | None = None
    created_at: str


class TicketList(BaseModel):
    count: int
    shop_date: str | None
    tickets: list[Ticket]


class RunStatus(BaseModel):
    run_id: str
    ticket_id: int
    status: Literal["running", "completed", "failed"]
    started_at: str
    finished_at: str | None = None
    report: BossReport | None = None
    pending_action_ids: list[str] = Field(default_factory=list)
    error: str | None = None


class Event(BaseModel):
    timestamp: str | None = None
    run_id: str | None = None
    step: int | None = None
    event: str | None = None
    agent: str | None = None
    ticket_id: int | None = None
    action: str | None = None
    delegation_source: str | None = None
    delegation_target: str | None = None
    delegation_depth: int | None = None
    mcp_tool: str | None = None
    tool_args: dict[str, Any] | None = None
    result_summary: str | None = None
    approval_status: str | None = None
    approval_pending: bool = False
    outcome: str | None = None
    error: str | None = None
    stop_or_continue: str | None = None


class EventList(BaseModel):
    count: int
    total_in_trail: int
    events: list[Event]


class ActionList(BaseModel):
    count: int
    actions: list[PreparedAction]


class ApproveRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=100, description="Name of the human approving")
    confirm: bool = Field(description="Must be true: set only by the explicit approval button")


class ApproveResponse(BaseModel):
    action: PreparedAction
    executed: bool
    checking_balance: float | None = Field(description="Checking balance after the decision, read via MCP")
    message: str


class CashBalance(BaseModel):
    account: str
    balance: float
    as_of: str
    source: str = "cash_accounts via MCP get_cash_account_balance"


class ResetRequest(BaseModel):
    confirm: bool = Field(description="Must be true to reset the working database")


class ResetResponse(BaseModel):
    reset: bool
    source: str
    target: str
    sha256: str
    original_unchanged: bool
    invalidated_pending_actions: int
    checking_balance: float | None
    message: str


# --------------------------------------------------------------------------
# App, state, errors
# --------------------------------------------------------------------------

RUNS: dict[str, RunStatus] = {}
_TASKS: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mcp = MCPGateway()
    app.state.store = ActionStore()
    app.state.audit = AuditTrail()
    try:
        yield
    finally:
        await app.state.mcp.close()


app = FastAPI(
    title="Campus Customs API",
    version="1.0.0",
    description="Dashboard API for the Campus Customs agent team. All shop data flows through the "
                "campus-customs MCP server; only POST /api/approvals/{action_id}/approve executes payments.",
    lifespan=lifespan,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse},
               409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
    max_age=600,
)


def _err(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"code": code, "message": message, "details": details}})


@app.exception_handler(ApiError)
async def _api_error(_: Request, exc: ApiError):
    return _err(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(orchestrator.ApprovalError)
async def _approval_error(_: Request, exc: orchestrator.ApprovalError):
    return _err(exc.status_code, exc.code, exc.message,
                exc.action.model_dump(mode="json") if exc.action else None)


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError):
    details = [{"loc": list(e.get("loc", [])), "msg": e.get("msg")} for e in exc.errors()]
    return _err(400, "invalid_request", "The request is invalid.", details)


@app.exception_handler(StarletteHTTPException)
async def _http_error(_: Request, exc: StarletteHTTPException):
    code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
    return _err(exc.status_code, code, str(exc.detail))


@app.exception_handler(MCPCallError)
async def _mcp_error(_: Request, exc: MCPCallError):
    return _err(500, "mcp_error", str(exc))


@app.exception_handler(Exception)
async def _unexpected(_: Request, exc: Exception):
    return _err(500, "internal_error", f"{type(exc).__name__}: unexpected server error")


def _audit(event: AuditEvent, **fields) -> None:
    RunState(run_id=fields.pop("run_id", "api"), audit=app.state.audit).log(event, **fields)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _checking_balance() -> float | None:
    res = await app.state.mcp.call("get_cash_account_balance", {"account_name": CHECKING})
    return res.get("balance") if res.get("found") else None


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health():
    shop_date, reachable = None, True
    try:
        d = await app.state.mcp.call("get_shop_date")
        shop_date = d.get("date_today")
    except MCPCallError:
        reachable = False
    ok = reachable and WORKING_DB.exists() and ORIGINAL_DB.exists()
    return HealthResponse(status="ok" if ok else "degraded", working_db_present=WORKING_DB.exists(),
                          original_db_present=ORIGINAL_DB.exists(), mcp_reachable=reachable,
                          model_configured=bool(os.environ.get("PORTKEY_API_KEY")),
                          model=config.MODEL_NAME, shop_date=shop_date)


@app.get("/api/tickets", response_model=TicketList, tags=["tickets"])
async def list_tickets():
    res = await app.state.mcp.call("list_tickets")
    date = (await app.state.mcp.call("get_shop_date")).get("date_today")
    tickets = [Ticket(**t, is_open=t["status"] == "open") for t in res["tickets"]]
    return TicketList(count=len(tickets), shop_date=date, tickets=tickets)


@app.post("/api/tickets/{ticket_id}/run", response_model=RunStatus, status_code=202, tags=["runs"])
async def run_ticket(ticket_id: int):
    if ticket_id <= 0:
        raise ApiError(400, "invalid_ticket_id", "ticket_id must be a positive integer.")
    t = await app.state.mcp.call("get_ticket_details", {"ticket_id": ticket_id})
    if not t.get("found"):
        raise ApiError(404, "ticket_not_found", f"No ticket with id {ticket_id}.")
    if t["status"] != "open":
        raise ApiError(409, "ticket_not_open", f"Ticket {ticket_id} is '{t['status']}', not open.")
    if any(r.ticket_id == ticket_id and r.status == "running" for r in RUNS.values()):
        raise ApiError(409, "run_in_progress", f"An agent run for ticket {ticket_id} is already in progress.")
    if not os.environ.get("PORTKEY_API_KEY"):
        raise ApiError(503, "model_not_configured",
                       "PORTKEY_API_KEY is not set in the backend environment; the agents cannot run.")

    run_id = uuid.uuid4().hex[:12]
    status = RunStatus(run_id=run_id, ticket_id=ticket_id, status="running", started_at=_now())
    RUNS[run_id] = status
    _audit(AuditEvent.API_REQUEST, run_id=run_id, ticket_id=ticket_id, action="POST /api/tickets/{id}/run",
           outcome="accepted", stop_or_continue="agent run started")

    async def _go():
        out = await orchestrator.run_tickets([ticket_id], run_id=run_id,
                                             audit=app.state.audit, store=app.state.store)
        status.finished_at = _now()
        status.report, status.pending_action_ids, status.error = out.report, out.action_ids, out.error
        status.status = "completed" if out.report else "failed"

    task = asyncio.create_task(_go())
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return status


@app.get("/api/runs/{run_id}", response_model=RunStatus, tags=["runs"])
async def get_run(run_id: str):
    if run_id not in RUNS:
        raise ApiError(404, "run_not_found", f"No run with id {run_id} in this server session.")
    return RUNS[run_id]


@app.get("/api/events", response_model=EventList, tags=["events"])
async def list_events(ticket_id: int | None = Query(None, ge=1), run_id: str | None = None,
                      agent: str | None = None, limit: int = Query(200, ge=1, le=1000)):
    path = config.AUDIT_PATH
    try:
        raw = json.loads(path.read_text()) if path.exists() and path.stat().st_size else []
    except json.JSONDecodeError as exc:
        raise AuditTrailCorrupt("audit trail is not valid JSON") from exc
    known = set(Event.model_fields)
    events = [Event(**{k: v for k, v in e.items() if k in known},
                    approval_pending=e.get("approval_status") == "pending_human_approval")
              for e in raw if isinstance(e, dict)]
    if ticket_id is not None:
        events = [e for e in events if e.ticket_id == ticket_id]
    if run_id:
        events = [e for e in events if e.run_id == run_id]
    if agent:
        events = [e for e in events if e.agent == agent]
    events = events[-limit:]
    return EventList(count=len(events), total_in_trail=len(raw), events=events)


@app.get("/api/approvals", response_model=ActionList, tags=["approvals"])
async def list_actions(status: str | None = Query(None, description="e.g. pending_human_approval"),
                       ticket_id: int | None = Query(None, ge=1)):
    actions = app.state.store.all()
    if status:
        actions = [a for a in actions if a.status == status]
    if ticket_id is not None:
        actions = [a for a in actions if a.ticket_id == ticket_id]
    return ActionList(count=len(actions), actions=actions)


@app.post("/api/approvals/{action_id}/approve", response_model=ApproveResponse, tags=["approvals"])
async def approve(action_id: str, body: ApproveRequest):
    if not body.confirm:
        raise ApiError(400, "confirmation_required", "confirm must be true (sent by the human approval button).")
    if not body.approved_by.strip():
        raise ApiError(400, "approver_required", "approved_by must name the human approver.")
    action, _ = await orchestrator.approve_action(action_id, body.approved_by, app.state.mcp,
                                                  store=app.state.store, audit=app.state.audit)
    balance = await _checking_balance()
    executed = action.status == "executed"
    if action.kind == "ticket_resolution":
        msg = f"Ticket {action.ticket_id} marked resolved."
    elif executed:
        msg = f"Payment executed; checking balance is now {balance}."
    else:
        msg = "Purchase approved and recorded. The system does not contact vendors; a human must place the order."
    return ApproveResponse(action=action, executed=executed, checking_balance=balance, message=msg)


@app.get("/api/cash/checking", response_model=CashBalance, tags=["cash"])
async def checking_balance():
    res = await app.state.mcp.call("get_cash_account_balance", {"account_name": CHECKING})
    if not res.get("found"):
        raise ApiError(404, "account_not_found", "No 'checking' account in cash_accounts.")
    return CashBalance(account=res["name"], balance=res["balance"], as_of=res["date"])


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


@app.post("/api/reset", response_model=ResetResponse, tags=["system"])
async def reset_working_db(body: ResetRequest):
    if not body.confirm:
        raise ApiError(400, "confirmation_required", "confirm must be true to reset the working database.")
    if any(r.status == "running" for r in RUNS.values()):
        raise ApiError(409, "run_in_progress", "An agent run is in progress; wait for it to finish.")
    if not ORIGINAL_DB.is_file():
        raise ApiError(500, "original_missing", "data/campus_customs.db is missing; cannot reset.")

    async with orchestrator._approval_lock:  # no approval can execute during the reset
        original_hash = _sha256(ORIGINAL_DB)
        await app.state.mcp.restart()  # close the MCP server and any SQLite handles it holds
        tmp = WORKING_DB.with_name(".campus_customs_new.db.resetting")
        shutil.copyfile(ORIGINAL_DB, tmp)  # read original -> write temp copy (direction: original -> working)
        with closing(sqlite3.connect(f"{tmp.as_uri()}?mode=ro", uri=True)) as c:
            if c.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                tmp.unlink(missing_ok=True)
                raise ApiError(500, "reset_failed", "Copied database failed the integrity check.")
        for suffix in ("-wal", "-shm", "-journal"):
            Path(str(WORKING_DB) + suffix).unlink(missing_ok=True)
        os.replace(tmp, WORKING_DB)
        new_hash = _sha256(WORKING_DB)
        unchanged = _sha256(ORIGINAL_DB) == original_hash
        invalidated = app.state.store.invalidate_pending("Working database was reset from the original.")

    balance = await _checking_balance()
    _audit(AuditEvent.DATABASE_RESET, action="POST /api/reset",
           tool_args={"source": "data/campus_customs.db", "target": "data/campus_customs_new.db"},
           result_summary=f"sha256 {new_hash[:16]}..., invalidated {invalidated} pending action(s)",
           outcome="reset" if new_hash == original_hash else "mismatch", stop_or_continue="done")
    if new_hash != original_hash or not unchanged:
        raise ApiError(500, "reset_failed", "Working copy does not match the original after reset.")
    return ResetResponse(reset=True, source="data/campus_customs.db", target="data/campus_customs_new.db",
                         sha256=new_hash, original_unchanged=unchanged,
                         invalidated_pending_actions=invalidated, checking_balance=balance,
                         message="Working database restored from the unchanged original.")
