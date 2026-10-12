"""Campus Customs MCP server.

Exposes narrow, purpose-specific tools over the working database
(data/campus_customs_new.db) so agents can gather evidence for the open
tickets. The original data/campus_customs.db is never opened.

All lookups are read-only. The single write tool, `execute_approved_payment`,
re-checks every payment rule inside one transaction, takes the amount from the
database (never from the caller), and is not exposed to any agent; the backend
only calls it after a human has explicitly approved a prepared payment.
"""

import calendar
from contextlib import closing
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "campus_customs_new.db"

PaymentKind = Literal["vendor_invoice", "lease_rent"]

# Names that may never appear as a payment approver: approval must come from a human.
AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service",
               "customer service", "agent", "system", "ai"}

mcp = FastMCP("campus-customs")


def _connect(read_only: bool = True) -> sqlite3.Connection:
    """Open the working database. Fails if the file is missing instead of
    silently creating an empty database."""
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Working database not found: {DB_PATH}")
    mode = "ro" if read_only else "rw"
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _query_one(sql: str, params: tuple) -> dict[str, Any] | None:
    with closing(_connect()) as conn:
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def _query_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with closing(_connect()) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _desk_date(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    return row["date_today"] if row else None


def _add_one_month(iso_date: str) -> str:
    d = date.fromisoformat(iso_date)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def _payment_check(conn: sqlite3.Connection, payment_kind: str,
                   reference_id: int, account_name: str) -> dict[str, Any]:
    """Deterministic payment rules shared by the feasibility check and the
    executor. Amount and payee always come from the database."""
    blockers: list[str] = []
    obligation: dict[str, Any] | None = None

    if payment_kind == "vendor_invoice":
        row = conn.execute(
            "SELECT i.id, i.amount, i.due_date, i.status, i.description, "
            "v.id AS vendor_id, v.name AS vendor_name "
            "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (reference_id,),
        ).fetchone()
        if row is None:
            blockers.append(f"No invoice with id {reference_id}.")
        else:
            obligation = {"amount": row["amount"], "payee": row["vendor_name"],
                          "due_date": row["due_date"], "invoice_status": row["status"],
                          "description": row["description"]}
            if row["status"] != "open":
                blockers.append(f"Invoice {reference_id} status is '{row['status']}', not 'open'.")
    elif payment_kind == "lease_rent":
        row = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due FROM leases WHERE id = ?",
            (reference_id,),
        ).fetchone()
        if row is None:
            blockers.append(f"No lease with id {reference_id}.")
        else:
            obligation = {"amount": row["monthly_rent"], "payee": row["landlord"],
                          "due_date": row["next_due"], "space_name": row["space_name"]}
    else:
        blockers.append(f"Unsupported payment_kind '{payment_kind}'.")

    prior = conn.execute(
        "SELECT id, amount, paid_at FROM payments WHERE kind = ? AND ref_id = ?",
        (payment_kind, reference_id),
    ).fetchall()
    prior_payments = [dict(p) for p in prior]
    if payment_kind == "vendor_invoice" and prior_payments:
        blockers.append(f"A payment is already recorded for invoice {reference_id}.")
    if payment_kind == "lease_rent" and obligation:
        # Rent for the current due period counts as paid if a payment was
        # recorded on or after the previous due date.
        due = date.fromisoformat(obligation["due_date"])
        prev_month = due.month - 1 or 12
        prev_year = due.year - 1 if due.month == 1 else due.year
        prev_due = date(prev_year, prev_month,
                        min(due.day, calendar.monthrange(prev_year, prev_month)[1])).isoformat()
        if any(p["paid_at"] > prev_due for p in prior_payments):
            blockers.append(f"Rent for lease {reference_id} already paid for the period due "
                            f"{obligation['due_date']}.")

    acct = conn.execute(
        "SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account_name,)
    ).fetchone()
    balance = acct["balance"] if acct else None
    if acct is None:
        blockers.append(f"No cash account named '{account_name}'.")

    balance_after = None
    if obligation and balance is not None:
        balance_after = round(balance - obligation["amount"], 2)
        if balance_after < 0:
            blockers.append(
                f"Insufficient funds: {account_name} balance {balance} is less than "
                f"amount {obligation['amount']}; payment would make the balance negative."
            )

    return {
        "payment_kind": payment_kind,
        "reference_id": reference_id,
        "obligation": obligation,
        "account_name": account_name,
        "account_balance": balance,
        "balance_after_payment": balance_after,
        "prior_payments": prior_payments,
        "shop_date": _desk_date(conn),
        "blockers": blockers,
    }


# --------------------------------------------------------------------------
# Read-only lookups
# --------------------------------------------------------------------------

@mcp.tool
def get_shop_date() -> dict[str, Any]:
    """Return the shop's current business date from `desk.date_today`.

    Agents must use this date, not the computer's clock, for due dates,
    overdue checks, and lead-time arrival estimates.
    """
    row = _query_one("SELECT date_today, notes FROM desk LIMIT 1", ())
    if row is None:
        return {"found": False, "message": "The desk table has no current date."}
    return {"found": True, **row}


@mcp.tool
def list_open_tickets() -> dict[str, Any]:
    """List every ticket whose status is 'open'.

    Reads the `tickets` table. Returns the full ticket rows so the Boss
    Agent can decide which specialists each ticket needs.
    """
    rows = _query_all(
        "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, "
        "status, notes, created_at FROM tickets WHERE status = 'open' ORDER BY id"
    )
    return {"count": len(rows), "tickets": rows}


@mcp.tool
def list_tickets() -> dict[str, Any]:
    """List every ticket regardless of status (open or resolved).

    Reads the `tickets` table. Used by the dashboard's ticket list so it can
    show whether each ticket is still open.
    """
    rows = _query_all(
        "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, "
        "status, notes, created_at FROM tickets ORDER BY id"
    )
    return {"count": len(rows), "tickets": rows}


@mcp.tool
def get_cash_account_balance(account_name: str) -> dict[str, Any]:
    """Return one cash account's current balance and as-of date.

    Reads the `cash_accounts` table. Returns found=False if the account does
    not exist.
    """
    row = _query_one("SELECT name, balance, date FROM cash_accounts WHERE name = ?",
                     (account_name,))
    if row is None:
        return {"found": False, "account_name": account_name,
                "message": "No cash account with this name."}
    return {"found": True, **row}


@mcp.tool
def list_cash_accounts() -> dict[str, Any]:
    """List every cash account with its balance and as-of date.

    Reads the `cash_accounts` table. Agents use it to find the real account
    name instead of guessing one.
    """
    rows = _query_all("SELECT name, balance, date FROM cash_accounts ORDER BY name")
    return {"count": len(rows), "accounts": rows}


@mcp.tool
def get_ticket_details(ticket_id: int) -> dict[str, Any]:
    """Look up one ticket by id, including its linked SKU/size, lease_id,
    and invoice_id. Reads the `tickets` table."""
    row = _query_one(
        "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, "
        "status, notes, created_at FROM tickets WHERE id = ?",
        (ticket_id,),
    )
    if row is None:
        return {"found": False, "ticket_id": ticket_id, "message": "No ticket with this id."}
    return {"found": True, **row}


@mcp.tool
def get_inventory_stock_for_sku_size(sku: str, size: str) -> dict[str, Any]:
    """Look up on-hand stock for one SKU in one size.

    Reads the `inventory` table. Returns the matching row (sku, name, size,
    qty, location), or found=False if no row exists for that SKU and size.
    """
    row = _query_one(
        "SELECT sku, name, size, qty, location FROM inventory "
        "WHERE sku = ? AND size = ?",
        (sku, size),
    )
    if row is None:
        return {"found": False, "sku": sku, "size": size,
                "message": "No inventory record for this SKU and size."}
    return {"found": True, **row}


@mcp.tool
def get_sku_cost_and_list_price(sku: str) -> dict[str, Any]:
    """Look up the unit cost and list price for one SKU.

    Reads the `pricing` table. Returns sku, unit_cost, and list_price, or
    found=False if the SKU has no pricing record.
    """
    row = _query_one(
        "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?",
        (sku,),
    )
    if row is None:
        return {"found": False, "sku": sku,
                "message": "No pricing record for this SKU."}
    return {"found": True, **row}


@mcp.tool
def get_lease_rent_and_cash_balance(lease_id: int, account_name: str) -> dict[str, Any]:
    """Look up a lease's rent obligation and the balance of a cash account.

    Reads the `leases` table (by id), the `cash_accounts` table (by name), and
    the rent payments already recorded for this lease in `payments` (so a
    notice can be checked against rent that was already paid; after a rent
    payment `next_due` moves to the following month). Each part is returned
    separately with its own found flag, so a missing lease or account is
    reported rather than filled in.
    """
    lease = _query_one(
        "SELECT id, space_name, landlord, monthly_rent, next_due, notes "
        "FROM leases WHERE id = ?",
        (lease_id,),
    )
    account = _query_one(
        "SELECT name, balance, date FROM cash_accounts WHERE name = ?",
        (account_name,),
    )
    rent_payments = _query_all(
        "SELECT id AS payment_id, amount, account, paid_at, approved_by FROM payments "
        "WHERE kind = 'lease_rent' AND ref_id = ? ORDER BY id",
        (lease_id,),
    )
    return {
        "recorded_rent_payments": rent_payments,
        "lease": {"found": True, **lease} if lease else
                 {"found": False, "lease_id": lease_id,
                  "message": "No lease with this id."},
        "cash_account": {"found": True, **account} if account else
                        {"found": False, "account_name": account_name,
                         "message": "No cash account with this name."},
    }


@mcp.tool
def get_invoice_with_vendor(invoice_id: int) -> dict[str, Any]:
    """Look up one vendor invoice and the vendor it is owed to.

    Reads `invoices` joined to `vendors`, plus `desk.date_today` to report
    whether an open invoice is past its due date and `payments` to show any
    recorded payment against it.
    """
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT i.id, i.vendor_id, i.amount, i.due_date, i.status, i.description, "
            "v.name AS vendor_name, v.specialty AS vendor_specialty, "
            "v.lead_days AS vendor_lead_days "
            "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
        if row is None:
            return {"found": False, "invoice_id": invoice_id,
                    "message": "No invoice with this id."}
        shop_date = _desk_date(conn)
        payments = [dict(p) for p in conn.execute(
            "SELECT id, amount, account, paid_at, approved_by FROM payments "
            "WHERE kind = 'vendor_invoice' AND ref_id = ?", (invoice_id,))]
    inv = dict(row)
    return {
        "found": True,
        **inv,
        "shop_date": shop_date,
        "is_past_due": bool(shop_date and inv["status"] == "open"
                            and inv["due_date"] < shop_date),
        "recorded_payments": payments,
    }


@mcp.tool
def list_vendors() -> dict[str, Any]:
    """List all vendors with their specialty and lead time in days.

    Reads the `vendors` table. The database has no SKU-to-vendor link, so
    callers must not treat a specialty match as a confirmed supplier.
    """
    rows = _query_all("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id")
    return {"count": len(rows), "vendors": rows}


@mcp.tool
def get_vendor_shipping_status(vendor_id: int) -> dict[str, Any]:
    """Check whether a vendor can ship new products and when they would arrive.

    Reads `vendors`, the vendor's `invoices`, and `desk.date_today`.
    Shop rule (enforced here): a vendor with any open, unpaid invoice will not
    ship new products, so `will_ship_new_orders` is False and the invoices are
    listed as blockers. `earliest_arrival_if_ordered_today` is the shop date
    plus the vendor's recorded lead_days and is only meaningful when the
    vendor will ship.
    """
    with closing(_connect()) as conn:
        vendor = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?",
            (vendor_id,),
        ).fetchone()
        if vendor is None:
            return {"found": False, "vendor_id": vendor_id,
                    "message": "No vendor with this id."}
        shop_date = _desk_date(conn)
        open_invoices = [dict(r) for r in conn.execute(
            "SELECT id, amount, due_date, status, description FROM invoices "
            "WHERE vendor_id = ? AND status = 'open' ORDER BY due_date",
            (vendor_id,))]
    for inv in open_invoices:
        inv["is_past_due"] = bool(shop_date and inv["due_date"] < shop_date)
    will_ship = not open_invoices
    arrival = None
    if shop_date:
        arrival = date.fromordinal(
            date.fromisoformat(shop_date).toordinal() + vendor["lead_days"]).isoformat()
    return {
        "found": True,
        **dict(vendor),
        "shop_date": shop_date,
        "open_unpaid_invoices": open_invoices,
        "will_ship_new_orders": will_ship,
        "blocked_reason": None if will_ship else
            "Vendor has open unpaid invoice(s); shop rule: vendor will not ship new products.",
        "earliest_arrival_if_ordered_today": arrival if will_ship else None,
        "earliest_arrival_once_unblocked": arrival,
    }


@mcp.tool
def check_payment_feasibility(payment_kind: PaymentKind, reference_id: int,
                              account_name: str) -> dict[str, Any]:
    """Check, without paying, whether a vendor invoice or lease rent could be
    paid from a cash account.

    Reads `invoices`/`vendors` or `leases`, `payments`, `cash_accounts`, and
    `desk`. The amount always comes from the database record. Returns the
    obligation, current balance, balance after payment, any blockers
    (not found, not open, already paid, insufficient funds / negative
    balance), and `decision`: 'ready_for_human_approval' or 'blocked'.
    Human approval is always required before any payment is executed.
    """
    with closing(_connect()) as conn:
        result = _payment_check(conn, payment_kind, reference_id, account_name)
    result["decision"] = "blocked" if result["blockers"] else "ready_for_human_approval"
    result["approval_required"] = True
    return result


# --------------------------------------------------------------------------
# Human-approved write (not exposed to any agent)
# --------------------------------------------------------------------------

@mcp.tool
def execute_approved_payment(payment_kind: PaymentKind, reference_id: int,
                             account_name: str, approved_by: str,
                             expected_amount: float | None = None) -> dict[str, Any]:
    """Execute ONE payment that a named human has explicitly approved.

    Re-checks every rule from `check_payment_feasibility` inside a single
    write transaction and refuses (status 'blocked') if any blocker exists,
    including insufficient funds. The amount comes from the database, the
    balance can never go negative, and `approved_by` must name a human.
    On success: inserts a `payments` row dated `desk.date_today`, reduces the
    cash balance, and marks a vendor invoice 'paid' or advances a lease's
    `next_due` by one month. If `expected_amount` is given (the amount the
    human saw when approving) and the database amount differs, the payment is
    refused as stale.
    """
    approver = (approved_by or "").strip()
    if not approver or approver.lower() in AGENT_NAMES or "agent" in approver.lower():
        return {"status": "blocked", "executed": False,
                "blockers": ["approved_by must name the human who approved this payment."]}

    conn = _connect(read_only=False)
    try:
        conn.execute("BEGIN IMMEDIATE")
        check = _payment_check(conn, payment_kind, reference_id, account_name)
        if check["blockers"]:
            conn.rollback()
            return {**check, "status": "blocked", "executed": False}
        amount = check["obligation"]["amount"]
        if expected_amount is not None and round(expected_amount, 2) != round(amount, 2):
            conn.rollback()
            return {**check, "status": "blocked", "executed": False,
                    "blockers": [f"Stale approval: approved amount {expected_amount} does not "
                                 f"match current database amount {amount}."]}
        cur = conn.execute(
            "UPDATE cash_accounts SET balance = balance - ?, date = ? "
            "WHERE name = ? AND balance >= ?",
            (amount, check["shop_date"], account_name, amount),
        )
        if cur.rowcount != 1:
            conn.rollback()
            return {**check, "status": "blocked", "executed": False,
                    "blockers": ["Insufficient funds at execution time."]}
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (payment_kind, reference_id, amount, account_name, check["shop_date"], approver),
        )
        payment_id = cur.lastrowid
        if payment_kind == "vendor_invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ? AND status = 'open'",
                         (reference_id,))
        else:
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?",
                         (_add_one_month(check["obligation"]["due_date"]), reference_id))
        new_balance = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (account_name,)
        ).fetchone()["balance"]
        if new_balance < 0:  # defensive: never commit a negative balance
            conn.rollback()
            return {"status": "failed", "executed": False,
                    "blockers": ["Balance would be negative; rolled back."]}
        conn.commit()
        return {"status": "executed", "executed": True, "payment_id": payment_id,
                "payment_kind": payment_kind, "reference_id": reference_id,
                "amount": amount, "account_name": account_name,
                "balance_after_payment": new_balance, "paid_at": check["shop_date"],
                "approved_by": approver}
    except Exception as exc:  # report, never half-apply
        conn.rollback()
        return {"status": "failed", "executed": False, "error": str(exc)}
    finally:
        conn.close()



@mcp.tool
def resolve_ticket(ticket_id: int, approved_by: str) -> dict[str, Any]:
    """Mark ONE open ticket as 'resolved' after a named human approved it.

    Human-only (no agent may call it): the backend calls it only from the
    approval route, after the Boss Agent reported the ticket's work complete
    and a human approved closing it. Refuses unknown or non-open tickets and
    non-human approvers. Changes only `tickets.status`.
    """
    approver = (approved_by or "").strip()
    if not approver or approver.lower() in AGENT_NAMES or "agent" in approver.lower():
        return {"status": "blocked", "executed": False,
                "blockers": ["approved_by must name the human who approved this resolution."]}
    conn = _connect(read_only=False)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            conn.rollback()
            return {"status": "blocked", "executed": False, "blockers": [f"No ticket with id {ticket_id}."]}
        if row["status"] != "open":
            conn.rollback()
            return {"status": "blocked", "executed": False,
                    "blockers": [f"Ticket {ticket_id} is '{row['status']}', not open."]}
        conn.execute("UPDATE tickets SET status = 'resolved' WHERE id = ? AND status = 'open'", (ticket_id,))
        conn.commit()
        return {"status": "executed", "executed": True, "ticket_id": ticket_id,
                "ticket_status": "resolved", "approved_by": approver}
    except Exception as exc:
        conn.rollback()
        return {"status": "failed", "executed": False, "error": str(exc)}
    finally:
        conn.close()

if __name__ == "__main__":
    mcp.run()
