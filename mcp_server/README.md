# Campus Customs MCP Server

A FastMCP server that gives the Campus Customs agents narrow access to the shop database so they can work on the open tickets (101, 102, 103). It doesn't allow arbitrary SQL. It is the **only** path from the agents to shop data.

**Database:** `data/campus_customs_new.db` (the working copy). The original `data/campus_customs.db` is never used. If the working database is missing, the server raises an error instead of creating an empty file. Every query is parameterized.

## Read-only tools

| Tool | Reads | Inputs | Returns |
|---|---|---|---|
| `get_shop_date` | `desk` | none | `found`, `date_today`, `notes` (the shop's current date) |
| `list_open_tickets` | `tickets` | none | `count`, `tickets[]` (full rows where `status = 'open'`) |
| `list_tickets` | `tickets` | none | `count`, `tickets[]` (every ticket, any status). Used by the dashboard API |
| `get_cash_account_balance` | `cash_accounts` | `account_name` | `found`, `name`, `balance`, `date`. Used by the dashboard API and the approval path |
| `list_cash_accounts` | `cash_accounts` | none | `count`, `accounts[]` (`name`, `balance`, `date`). Agents use it to find the real account name instead of guessing |
| `get_ticket_details` | `tickets` | `ticket_id` | `found`, plus all ticket fields, including `sku`, `size`, `qty`, `lease_id`, `invoice_id` |
| `get_inventory_stock_for_sku_size` | `inventory` | `sku`, `size` | `found`, `sku`, `name`, `size`, `qty`, `location` |
| `get_sku_cost_and_list_price` | `pricing` | `sku` | `found`, `sku`, `unit_cost`, `list_price` |
| `get_lease_rent_and_cash_balance` | `leases`, `cash_accounts`, `payments` | `lease_id`, `account_name` | `lease` {`found`, `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`}, `cash_account` {`found`, `name`, `balance`, `date`}, `recorded_rent_payments[]` (`payment_id`, `amount`, `account`, `paid_at`, `approved_by`) |
| `get_invoice_with_vendor` | `invoices`, `vendors`, `payments`, `desk` | `invoice_id` | `found`, invoice fields, `vendor_name`, `vendor_specialty`, `vendor_lead_days`, `shop_date`, `is_past_due`, `recorded_payments[]` |
| `list_vendors` | `vendors` | none | `count`, `vendors[]` (`id`, `name`, `specialty`, `lead_days`) |
| `get_vendor_shipping_status` | `vendors`, `invoices`, `desk` | `vendor_id` | `found`, vendor fields, `shop_date`, `open_unpaid_invoices[]`, `will_ship_new_orders`, `blocked_reason`, `earliest_arrival_if_ordered_today`, `earliest_arrival_once_unblocked` |
| `check_payment_feasibility` | `invoices`/`vendors` or `leases`, `payments`, `cash_accounts`, `desk` | `payment_kind` (`vendor_invoice` \| `lease_rent`), `reference_id`, `account_name` | `obligation` (amount, payee and due date from the database), `account_balance`, `balance_after_payment`, `prior_payments[]`, `blockers[]`, `decision` (`ready_for_human_approval` \| `blocked`), `approval_required: true` |

When a requested record doesn't exist, a lookup returns `found: false` with a message. It never returns a substitute value.

### Rules enforced in code
- **Shop date:** "today" always means `desk.date_today`.
- **Vendor blocker:** a vendor with any open, unpaid invoice won't ship new products, so `will_ship_new_orders` is `false`.
- **Lead time:** arrival dates are `desk.date_today` plus the vendor's recorded `lead_days`.
- **Payment amounts** always come from the database record. The caller can't supply an amount.
- **Payment blockers:** the payment is blocked if the record is missing, the invoice isn't `open`, it has already been paid, the account is missing, or the funds are insufficient (the balance would go negative).

## Human-approved write tools

| Tool | Writes | Inputs | Returns |
|---|---|---|---|
| `execute_approved_payment` | `payments`, `cash_accounts`, and either `invoices.status` or `leases.next_due` | `payment_kind`, `reference_id`, `account_name`, `approved_by`, optional `expected_amount` | `status` (`executed` \| `blocked` \| `failed`), `executed`, `payment_id`, `amount`, `balance_after_payment`, `paid_at`, `approved_by`, or `blockers` |
| `resolve_ticket` | `tickets.status` (open → resolved) | `ticket_id`, `approved_by` | `status` (`executed` \| `blocked` \| `failed`), `ticket_id`, `ticket_status`, `approved_by`, or `blockers` (unknown ticket, not open, non-human approver) |

- **Same rules, rechecked:** it re-runs every feasibility rule inside one transaction. The deduction is guarded with `balance >= amount`, so it never commits a negative balance.
- **Stale approvals refused:** if `expected_amount` (the amount the human approved) differs from the current database amount, the payment is refused as stale.
- **Human approver required:** `approved_by` must name a human. Agent or system names are rejected.
- **What it records:** the payment row is dated `desk.date_today`. A paid invoice becomes `paid`. A rent payment moves the lease's `next_due` forward one month. This is a design choice; the original data has no paid-rent example.
- **No agent can call it.** Only the backend's human-approval path (`backend/orchestrator.approve_action`, reached only through `POST /api/approvals/{action_id}/approve`) calls it.

## Running

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python mcp_server/server.py
```

Claude Code connects through the project's `.mcp.json`.

**Tool count:** 15 (13 read-only, 2 human-only writes). Agents can never call `execute_approved_payment` or `resolve_ticket`. The backend calls them only from `POST /api/approvals/{action_id}/approve` after a person approves.
