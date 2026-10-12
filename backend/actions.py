"""Store of actions the agents prepared and that wait for a human decision.

Persisted at output/pending_actions.json. Agent runs register payment and
purchase proposals here; only the approval route can move an action out of
`pending_human_approval`. Every status change is a compare-and-set under a
file lock, so an action can be claimed for execution only once.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Literal

from pydantic import BaseModel, Field

from .config import PROJECT_ROOT

ACTIONS_PATH = PROJECT_ROOT / "output" / "pending_actions.json"

ActionKind = Literal["payment", "purchase", "ticket_resolution"]
StoredStatus = Literal["pending_human_approval", "executing", "executed", "approved",
                       "blocked", "failed", "stale"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PreparedAction(BaseModel):
    action_id: str = Field(default_factory=lambda: "act_" + uuid.uuid4().hex[:10])
    kind: ActionKind
    run_id: str
    ticket_id: int | None
    prepared_by: str
    description: str
    status: StoredStatus = "pending_human_approval"
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)
    # payment fields (as prepared from check_payment_feasibility)
    payment_kind: Literal["vendor_invoice", "lease_rent"] | None = None
    reference_id: int | None = None
    account_name: str | None = None
    amount: float | None = None
    payee: str | None = None
    balance_after_at_preparation: float | None = None
    # decision / execution
    approved_by: str | None = None
    payment_id: int | None = None
    balance_after: float | None = None
    blockers: list[str] = Field(default_factory=list)
    note: str | None = None


class ActionStore:
    def __init__(self, path: Path = ACTIONS_PATH):
        self.path = path

    @contextmanager
    def _locked(self) -> Iterator[list[dict]]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path.with_suffix(".lock"), "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = json.loads(self.path.read_text()) if self.path.exists() and self.path.stat().st_size else []
            yield data
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            os.replace(tmp, self.path)

    def all(self) -> list[PreparedAction]:
        if not self.path.exists() or not self.path.stat().st_size:
            return []
        return [PreparedAction(**d) for d in json.loads(self.path.read_text())]

    def get(self, action_id: str) -> PreparedAction | None:
        return next((a for a in self.all() if a.action_id == action_id), None)

    def add(self, action: PreparedAction) -> PreparedAction:
        """Add an action unless an identical one is already pending; return the stored one."""
        with self._locked() as data:
            for d in data:
                if (d["status"] == "pending_human_approval" and d["kind"] == action.kind
                        and d.get("payment_kind") == action.payment_kind
                        and d.get("reference_id") == action.reference_id
                        and d.get("account_name") == action.account_name
                        and d.get("amount") == action.amount
                        and (action.kind == "payment" or d.get("ticket_id") == action.ticket_id)
                        and (action.kind != "purchase" or d.get("description") == action.description)):
                    return PreparedAction(**d)
            data.append(action.model_dump())
        return action

    def transition(self, action_id: str, expected: StoredStatus, new: StoredStatus,
                   **fields) -> PreparedAction | None:
        """Atomically move an action from `expected` to `new`. Returns None if
        the action is not in the expected state (someone else got there first)."""
        with self._locked() as data:
            for d in data:
                if d["action_id"] == action_id:
                    if d["status"] != expected:
                        return None
                    d.update(fields, status=new, updated_at=_now())
                    return PreparedAction(**d)
        return None

    def invalidate_pending(self, reason: str) -> int:
        n = 0
        with self._locked() as data:
            for d in data:
                if d["status"] == "pending_human_approval":
                    d.update(status="stale", note=reason, updated_at=_now())
                    n += 1
        return n
