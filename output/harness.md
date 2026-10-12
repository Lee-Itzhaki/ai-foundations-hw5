# Campus Customs — Database Harness

> **How to read this file:** the Problem 2–7 sections below record the system as it was at each stage. The system grew afterwards; for example, the MCP server went from 13 to 15 tools in Problem 9. The **[Final System Reference](#final-system-reference-problem-9)** at the end describes the system exactly as implemented now and takes precedence wherever the two differ.

Source: `data/campus_customs.db` (original) and `data/campus_customs_new.db` (working copy).
Both files were inspected **read-only** (`mode=ro&immutable=1`). At inspection time they were byte-identical
(SHA-256 `23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a`, 53,248 bytes each).

Conventions in this document:

- **Declared** = enforced/stated in the SQLite schema (`PRIMARY KEY`, `FOREIGN KEY`).
- **Inference** = a reasonable reading of column names and data that the schema does *not* declare.
- The schema does not name any agents. Agent roles below are **inferences** drawn from the ticket types
  (`customer_order`, `rent_notice`, `price_override`) and the table contents.

The database has 9 tables: `desk`, `inventory`, `pricing`, `vendors`, `leases`, `cash_accounts`, `payments`, `invoices`, `tickets`.

---

## `desk` (1 row)

| Column | Type | Constraints |
|---|---|---|
| `date_today` | TEXT | NOT NULL |
| `notes` | TEXT | nullable |

- **Keys:** no primary key; no foreign keys.
- **Data:** `date_today = 2026-08-31`, `notes = NULL`.
- **Why it matters:** It holds the shop's "current date," which every agent needs for judging due dates, overdue invoices, and rent timing (inference: shared by all agents).

## `inventory` (10 rows)

| Column | Type | Constraints |
|---|---|---|
| `sku` | TEXT | NOT NULL, part of PK |
| `name` | TEXT | NOT NULL |
| `size` | TEXT | NOT NULL, part of PK |
| `qty` | INTEGER | NOT NULL |
| `location` | TEXT | NOT NULL |

- **Keys:** composite primary key `(sku, size)`; no declared foreign keys.
- **Relationships (inference):** `sku` matches `pricing.sku`; `(sku, size)` matches `tickets.(sku, size)`.
- **Data highlights:** `CC-TEE-WHITE` size S and `CC-MUG-CREST` OS both have `qty = 0`.
- **Why it matters:** It is the stock count, so an order or fulfillment agent needs it to check whether a requested item and size can be supplied (inference).

## `pricing` (4 rows)

| Column | Type | Constraints |
|---|---|---|
| `sku` | TEXT | PRIMARY KEY |
| `unit_cost` | REAL | NOT NULL |
| `list_price` | REAL | NOT NULL |

- **Keys:** primary key `sku`; no declared foreign keys.
- **Relationships (inference):** one `pricing` row per SKU present in `inventory` (all 4 inventory SKUs have a pricing row).
- **Why it matters:** Cost and list price set the margin, so a pricing or discount agent needs them for price-override requests (inference).

## `vendors` (3 rows)

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY |
| `name` | TEXT | NOT NULL |
| `specialty` | TEXT | NOT NULL |
| `lead_days` | INTEGER | NOT NULL |

- **Keys:** primary key `id`; referenced by `invoices.vendor_id` (declared).
- **Data:** 1 Bulldog Print Co (apparel reprint, 5 days), 2 Elm City Gifts (mugs and small goods, 3 days), 3 QuickShip CT (local courier, 1 day).
- **Note:** No table links vendors directly to SKUs. Any matching of vendor to product by `specialty` is an inference.
- **Why it matters:** Lead times and specialties tell a restocking or ordering agent who can supply what and how fast; it is also needed to identify who an invoice is owed to (inference).

## `leases` (1 row)

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY |
| `space_name` | TEXT | NOT NULL |
| `landlord` | TEXT | NOT NULL |
| `monthly_rent` | REAL | NOT NULL |
| `next_due` | TEXT | NOT NULL |
| `notes` | TEXT | nullable |

- **Keys:** primary key `id`; referenced by `tickets.lease_id` (declared).
- **Data:** lease 1, "Chapel Street shop", landlord Elm City Properties, $2,400.00/month, next due 2026-09-02.
- **Why it matters:** It records the rent obligation, so a finance or payments agent needs it to verify and schedule rent (inference).

## `cash_accounts` (1 row)

| Column | Type | Constraints |
|---|---|---|
| `name` | TEXT | PRIMARY KEY |
| `balance` | REAL | NOT NULL |
| `date` | TEXT | NOT NULL |

- **Keys:** primary key `name`; no declared foreign keys.
- **Relationships (inference):** `payments.account` likely refers to `cash_accounts.name`. This is not declared.
- **Data:** `checking`, balance $3,400.00 as of 2026-08-31.
- **Why it matters:** The available cash limits what a finance agent can pay (inference).

## `payments` (0 rows)

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY |
| `kind` | TEXT | NOT NULL |
| `ref_id` | INTEGER | nullable |
| `amount` | REAL | NOT NULL |
| `account` | TEXT | NOT NULL |
| `paid_at` | TEXT | NOT NULL |
| `approved_by` | TEXT | NOT NULL |

- **Keys:** primary key `id`; **no declared foreign keys**.
- **Relationships (inference):** `ref_id` probably points to an `invoices.id` or `leases.id` depending on `kind`, and `account` probably points to `cash_accounts.name`. The schema does not enforce either.
- **Data:** empty, so no payments have been recorded.
- **Why it matters:** It is the payment ledger, where a finance agent would record payments. `approved_by` (NOT NULL) suggests every payment needs a named approver (inference).

## `invoices` (1 row)

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY |
| `vendor_id` | INTEGER | NOT NULL, FK → `vendors(id)` |
| `amount` | REAL | NOT NULL |
| `due_date` | TEXT | NOT NULL |
| `status` | TEXT | NOT NULL |
| `description` | TEXT | nullable |

- **Keys:** primary key `id`; declared foreign key `vendor_id → vendors.id`; referenced by `tickets.invoice_id` (declared).
- **Data:** invoice 501, vendor 1 (Bulldog Print Co), $840.00, due 2026-08-28, status `open`, "Rush reprint CC-TEE-WHITE S".
- **Why it matters:** It records what the shop owes vendors, so a finance agent needs it to pay bills. It also ties a restock in progress to a customer order (see ticket 101).

## `tickets` (3 rows)

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY |
| `type` | TEXT | NOT NULL |
| `requester` | TEXT | NOT NULL |
| `subject` | TEXT | NOT NULL |
| `sku` | TEXT | nullable |
| `size` | TEXT | nullable |
| `qty` | INTEGER | nullable |
| `lease_id` | INTEGER | nullable, FK → `leases(id)` |
| `invoice_id` | INTEGER | nullable, FK → `invoices(id)` |
| `status` | TEXT | NOT NULL |
| `notes` | TEXT | nullable |
| `created_at` | TEXT | NOT NULL |

- **Keys:** primary key `id`; declared foreign keys `lease_id → leases.id` and `invoice_id → invoices.id`.
- **Relationships (inference):** `(sku, size)` matches `inventory.(sku, size)` and `sku` matches `pricing.sku`. Neither is declared.
- **Why it matters:** It is the work queue. Each ticket's `type` suggests which agent should handle it (inference: orders → inventory/fulfillment, rent notices → finance, price overrides → pricing).

---

## Relationship Summary

**Declared foreign keys**

- `invoices.vendor_id` → `vendors.id`
- `tickets.invoice_id` → `invoices.id`
- `tickets.lease_id` → `leases.id`

**Undeclared links (inference, based on matching names and values)**

- `inventory.sku` ↔ `pricing.sku`
- `tickets.(sku, size)` → `inventory.(sku, size)`, and `tickets.sku` → `pricing.sku`
- `payments.account` → `cash_accounts.name`
- `payments.ref_id` → `invoices.id` or `leases.id`, depending on `payments.kind`
- `invoices.description` mentions a SKU and size in free text ("CC-TEE-WHITE S"), but there is no structured SKU column.

**Unlinked tables:** `desk` stands alone and supplies the reference date.

Note: SQLite enforces foreign keys only when `PRAGMA foreign_keys = ON` is set on a connection.

```
vendors ──< invoices ──< tickets >── leases
                            │
                    (sku,size)·····> inventory ·····> pricing   (····· = inferred)
payments ·····> cash_accounts / invoices / leases               (inferred)
desk  (standalone: current date)
```

---

## Open Tickets and Related Records

Reference date from `desk.date_today`: **2026-08-31**. All three tickets have `status = 'open'`. Nothing was resolved or modified.

### Ticket 101: `customer_order`, "Bulldog tee"

- **Requester:** Tauhid Zaman. **Created:** 2026-08-31T09:15-04:00.
- **Request:** `CC-TEE-WHITE`, size S, qty 1. Notes: "Needs a tee in size S."
- **inventory** `(CC-TEE-WHITE, S)`: Classic Bulldog Tee, **qty 0**, Aisle B. The requested size is out of stock.
- **pricing** `CC-TEE-WHITE`: unit cost $8.00, list price $28.00.
- **invoices** 501 (via the declared `invoice_id` FK): $840.00 to vendor 1, description "Rush reprint CC-TEE-WHITE S", due **2026-08-28**, status `open`. The due date is 3 days before the desk date and the invoice is still open.
- **vendors** 1 (via `invoices.vendor_id`): Bulldog Print Co, apparel reprint, lead time 5 days.
- **Inference:** The order depends on a rush reprint of the out-of-stock size, and that reprint's invoice is past due and unpaid.

### Ticket 102: `rent_notice`, "Rent due"

- **Requester:** Elm City Properties. **Created:** 2026-08-31T11:05-04:00.
- **Notes:** "Email: shop rent due in 2 days."
- **leases** 1 (via the declared `lease_id` FK): Chapel Street shop, landlord Elm City Properties, $2,400.00/month, next due **2026-09-02**. That date is 2 days after the desk date, which matches the notice, and the requester matches the landlord.
- **cash_accounts** `checking`: $3,400.00 as of 2026-08-31.
- **payments:** none recorded.
- **Observation (arithmetic only):** Rent ($2,400) plus open invoice 501 ($840) totals $3,240, which is within the $3,400 balance and would leave $160. No payment was made.

### Ticket 103: `price_override`, "Bulk hoodie discount"

- **Requester:** Yale AI Club. **Created:** 2026-08-31T16:55-04:00.
- **Request:** `CC-HOOD-NAVY`, size M, qty 20. Notes: "Student org wants 20 hoodies, size M, asking for a bulk discount."
- **inventory** `(CC-HOOD-NAVY, M)`: Basic Hoodie Big Yale, **qty 8**, Aisle A. The request is **12 units short**. Other sizes on hand: S 4, L 14, XL 6.
- **pricing** `CC-HOOD-NAVY`: unit cost $22.00, list price $58.00. At list price, 20 units would be $1,160.00 against a cost of $440.00.
- **No linked lease or invoice.**
- **Inference:** Vendor 1 (Bulldog Print Co, apparel reprint, 5-day lead) is the only apparel vendor, but no table links vendors to SKUs. The schema stores no discount policy or price floor.

---

## Problem 3: MCP Server Tools

Server: `mcp_server/server.py` (FastMCP). It reads only `data/campus_customs_new.db`, opened read-only. All queries are parameterized. A missing record returns `found: false` and is never filled in.

### Tool 1: `get_inventory_stock_for_sku_size`

- **Input parameters:** `sku` (str), `size` (str)
- **Output fields:** `found`, `sku`, `name`, `size`, `qty`, `location`
- **Table read:** `inventory`
- **Ticket unlocked:** 101 (also usable for the stock side of 103)
- **Why:** Ticket 101 asks for one `CC-TEE-WHITE` tee in size S. Looking up `(sku, size)` returns the exact `qty` (currently 0), so the agent can confirm the order can't be filled from stock and needs the open rush reprint (invoice 501).

### Tool 2: `get_lease_rent_and_cash_balance`

- **Input parameters:** `lease_id` (int), `account_name` (str)
- **Output fields:** `lease` {`found`, `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`}; `cash_account` {`found`, `name`, `balance`, `date`}
- **Tables read:** `leases`, `cash_accounts`
- **Ticket unlocked:** 102
- **Why:** Ticket 102 is a landlord's notice tied to `lease_id` 1. The tool returns the lease's `landlord`, `monthly_rent` ($2,400) and `next_due` (2026-09-02) next to the `checking` `balance` ($3,400), so the agent can confirm the notice is genuine and that cash covers the rent before anyone approves a payment.

### Tool 3: `get_sku_cost_and_list_price`

- **Input parameters:** `sku` (str)
- **Output fields:** `found`, `sku`, `unit_cost`, `list_price`
- **Table read:** `pricing`
- **Ticket unlocked:** 103
- **Why:** Ticket 103 asks for a bulk discount on 20 `CC-HOOD-NAVY` hoodies. The tool returns the hoodie's `unit_cost` ($22) and `list_price` ($58), which bound any discount the agent can offer without selling below cost.

**Coverage note:** No tool reads `invoices` or `vendors`. The status of invoice 501 (ticket 101's linked reprint) and vendor lead times can't be retrieved through this server yet.

---

## Problem 5: Agent Team (PydanticAI)

Code lives in `backend/`:
- `models.py`: shared Pydantic models
- `agents.py`: the five agents, MCP access, delegation and validators
- `orchestrator.py`: runs and the human-approved payment path
- `config.py`: model and limits
- `audit.py`: the audit trail
- `prompts/`: one prompt file per agent

Every agent uses **`gpt-6-luna` through Portkey**. The key is read from `PORTKEY_API_KEY` at runtime, and the base URL can be overridden with `PORTKEY_BASE_URL`. The agents reach shop data **only** through the `campus-customs` MCP server.

### Agents

| Agent | Prompt file | Responsibilities | Boundaries |
|---|---|---|---|
| **Boss** | `boss.md` | Reads open tickets and the shop date, delegates to specialists, coordinates multi-agent tickets, tracks each task (succeeded / partial / blocked / failed / needs human approval), returns a `BossReport`. | Does no specialist work. Never writes a resolution no specialist produced. Can only pass along payment proposals and drafts that specialists actually returned (checked in code). |
| **Inventory** | `inventory.md` | Stock by SKU and size, cost and list price, vendors, lead times, vendor shipping blockers, restock proposals. | Never invents stock, prices, vendors or lead times. Matching a vendor by specialty is labelled an inference. No vendor contact or orders. Discounts are human decisions. |
| **Accounting** | `accounting.md` | Invoices, cash, payment feasibility, payment proposals. | Must run `check_payment_feasibility` before proposing a payment. Proposals must match that result exactly (checked in code). Cannot execute payments. Never assumes cash inflows. |
| **Facilities** | `facilities.md` | Leases, landlords, rent due dates, locations, facilities follow-ups. Verifies notices against the lease record. | Hands payment checks to Accounting. No landlord contact, no lease changes, no invented terms or fees. |
| **Customer Service** | `customer_service.md` | Customer-ticket analysis and internal `CustomerDraft`s (`status: proposed`, `sent: false`). | Never sends anything or contacts anyone. Never promises an unsupported outcome. Never claims an action was completed. |

### How delegation works
- **Full connectivity.** Every agent has a `delegate_task(DelegationRequest)` tool that can reach any other agent. The request carries `target_agent`, `ticket_id`, `task` and `known_facts` (each with its MCP source). The code, not the model, fills in the source agent and the depth.
- **Structured results.** The target runs with its own prompt and allowed tools, and returns a structured `AgentResult`: status, evidence, payment proposals, customer drafts, proposed actions, errors and `return_to_boss_reason`. Its `delegations` list is filled from the run record, not by the model.
- **Boss stays in charge.** The Boss Agent is the root of every normal run. Specialists can delegate sideways, but their results always flow back up the chain to the Boss.
- **Limits, enforced in code:**
  - delegation depth of at most **3**
  - at most **12** delegations per run
  - no self-delegation
  - no delegation to an agent already in the current chain (prevents cycles)
  - a run-wide step budget

  A refused delegation returns a `blocked` `AgentResult` with `ErrorCode.delegation_limit` and is audited.
- **Shared token budget.** Sub-runs share the parent's usage counter, so the token and request budget covers the whole run.

### MCP tools: tables, agents, tickets

**Existing tools (Problem 3)**

| Tool | Tables | Used by | Ticket | How the returned fields help |
|---|---|---|---|---|
| `get_inventory_stock_for_sku_size` | `inventory` | Inventory, Customer Service | 101, 103 | **101:** `qty` = 0 for `CC-TEE-WHITE` / S shows the order can't be filled from stock. **103:** `qty` = 8 for `CC-HOOD-NAVY` / M against the 20 requested gives a shortfall of 12. |
| `get_sku_cost_and_list_price` | `pricing` | Inventory, Customer Service | 103 (also 101) | `unit_cost` $22 and `list_price` $58 bound any bulk discount a human could approve without selling below cost. For 101, it gives the $28 tee price for the draft reply. |
| `get_lease_rent_and_cash_balance` | `leases`, `cash_accounts` | Facilities, Accounting | 102 | `landlord` matches the requester. `next_due` 2026-09-02 matches "due in 2 days". `monthly_rent` $2,400 sits next to the `checking` `balance` of $3,400. |

**New tools (Problem 5)**

| Tool | Tables | Used by | Ticket | How the returned fields help |
|---|---|---|---|---|
| `get_shop_date` | `desk` | All agents | 101, 102, 103 | `date_today` (2026-08-31) is the shop's "today" for every overdue, due-in and arrival calculation, as the shop rules require. |
| `list_open_tickets` | `tickets` | Boss | 101, 102, 103 | Returns the three open tickets with `type`, `sku`, `size`, `qty`, `lease_id` and `invoice_id`, so the Boss can route each one to the right specialists. |
| `get_ticket_details` | `tickets` | All agents | 101, 102, 103 | Lets a specialist re-read the exact request (for example 20 × size M for 103) and its linked `invoice_id` or `lease_id` instead of relying on a paraphrase. |
| `get_invoice_with_vendor` | `invoices`, `vendors`, `payments`, `desk` | Accounting | 101 | For invoice 501 (linked from ticket 101), returns $840, due 2026-08-28, `status` open, `is_past_due` true, the vendor Bulldog Print Co, and no recorded payments. That shows the S-size reprint is unpaid and overdue. |
| `list_vendors` | `vendors` | Inventory | 103 (also 101) | Lists vendors with `specialty` and `lead_days`, so Inventory can name the apparel vendor as a *labelled inference* (there's no SKU-to-vendor link) when planning a restock of 12 hoodies. |
| `get_vendor_shipping_status` | `vendors`, `invoices`, `desk` | Inventory | 101, 103 | For vendor 1, `will_ship_new_orders` is false because of open invoice 501, so restocking either the tee (101) or the hoodies (103) is **blocked** until it's paid. `earliest_arrival_once_unblocked` (2026-09-05 = desk date + 5 lead days) is the earliest possible date. |
| `check_payment_feasibility` | `invoices`/`vendors` or `leases`, `payments`, `cash_accounts`, `desk` | Accounting | 102, 101 | **102:** rent $2,400 from checking leaves `balance_after_payment` of $1,000, so the decision is `ready_for_human_approval`. **101:** invoice 501 for $840 is also payable. Checked separately, they total $3,240, which leaves $160. Any shortfall becomes a `blocked` decision. |
| `execute_approved_payment` | writes `payments`, `cash_accounts`, `invoices` / `leases` | **No agent.** Human-approval path only. | 102, 101 (later) | Runs only after a human approves. It rechecks the rules, takes the amount from the database, and refuses insufficient funds or any negative balance. |

### Audit trail
- **Where:** every run appends structured `AuditEntry` records to `output/audit_trail.json`.
- **When:**
  - run start and finish
  - each MCP tool call (agent, tool, redacted arguments, short result summary, outcome)
  - each delegation and its return (source, target, depth, status)
  - refused delegations
  - limit hits
  - approval requests and decisions
  - errors
- **Common fields:** each entry also carries a timestamp, run ID, step number, ticket ID, approval status and a stop/continue reason.
- **Append-only:** the file is re-read and atomically rewritten under a file lock. A corrupt file is never overwritten.
- **Not recorded:** no hidden reasoning, prompts or keys. Keys and secret-looking values are redacted.

---

## Safety Controls

- **Human approval for payments.** No agent has a tool that pays. `execute_approved_payment` is excluded from every agent's allow-list *and* refused by the MCP call hook. Only `orchestrator.execute_human_approved_payment`, given a named human approver, can call it. Agent proposals are always `pending_human_approval` or `blocked`, and validators reject any agent-claimed approval.
- **Insufficient-funds protection.** `check_payment_feasibility` and `execute_approved_payment` both block when `balance < amount`. The executor rechecks inside a write transaction.
- **No negative balances.** The deduction is guarded with `WHERE balance >= amount`, with a defensive rollback if the balance would be negative. Accounting is also instructed to check combined proposals against the balance, and never to assume inflows.
- **No unauthorized contact.** No tool can send email or contact customers or vendors. Customer drafts are typed `sent: false` and `status: proposed`, and only Customer Service may create them (checked in code).
- **No invented shop facts.** Every `Evidence` item must name an MCP tool that was actually called in the run, and validators make the model retry otherwise. Payment proposals must equal a feasibility result exactly. Not-found results are explicit (`found: false`).
- **MCP-only database access.** The backend has no SQL or database helper. All facts come through `MCPToolset` over stdio to `mcp_server/server.py`, which opens only `data/campus_customs_new.db`. Each agent sees only its allow-listed tools.
- **API keys and sensitive data.** `PORTKEY_API_KEY` is read from the environment only. It is never in code, prompts, docs or outputs. The audit log redacts secret-like keys and values, and stores short summaries rather than full transcripts.
- **Maximum steps and delegation depth:**
  - delegation depth 3
  - 12 delegations per run
  - 80 audited steps per run
  - 2 output-validation retries per agent run
  - 1 retry per failed MCP tool call
- **Tool-call and token budgets.** One `UsageLimits` covers the whole run, shared by sub-agents: 40 model requests, 60 tool calls, 250,000 total tokens. Exceeding it stops the run with a `limit_reached` audit entry.
- **Stopping behavior:**
  - after 4 failed or not-found MCP results in a run, the hook refuses further calls and tells the agent to report the missing data
  - refused delegations come back as `blocked`
  - missing records are reported, not filled in
  - anything that needs a human ends as `needs_human_approval`, and the Boss lists it under `human_decisions_needed`

---

## Problem 7: FastAPI Backend

`backend/main.py` is run from `backend/` with `uvicorn main:app --reload --port 8000` and serves `http://localhost:8000`. OpenAPI docs are at `/docs` and `/openapi.json`.

The routes reuse the agent team (`orchestrator.run_tickets`), the Pydantic models, the audit trail, and the **same MCP server**, through `backend/mcp_client.py`. There is no direct SQL for shop data. The only file-level database operation is the reset copy. Prepared actions persist in `output/pending_actions.json` (`backend/actions.py`).

To support the API, two read-only MCP tools were added:
- `list_tickets`: every ticket, any status
- `get_cash_account_balance`

`execute_approved_payment` also gained an optional `expected_amount` stale-check. The MCP server now has 13 tools.

### Routes

| Method | URL | What it does | Request input | Main response | Dashboard caller |
|---|---|---|---|---|---|
| GET | `/api/health` | Checks that both DB files exist, that MCP is reachable, and that a model key is configured | — | `HealthResponse` {status, working_db_present, original_db_present, mcp_reachable, model_configured, model, shop_date} | Status indicator in the header |
| GET | `/api/tickets` | Lists tickets 101–103 via MCP `list_tickets` | — | `TicketList` {count, shop_date, tickets[] with all fields + `status` + `is_open`} | Ticket tabs / ticket list |
| POST | `/api/tickets/{ticket_id}/run` | Validates the ticket (400 bad ID, 404 missing, 409 not open or already running, 503 no API key), then starts the Boss Agent in the background | path `ticket_id` | **202** `RunStatus` {run_id, ticket_id, status `running`, started_at} | "Run agents" button on each ticket tab |
| GET | `/api/runs/{run_id}` | Returns a run's status and result | path `run_id` | `RunStatus` {status `running`/`completed`/`failed`, report (`BossReport`), pending_action_ids, error} | Polling after "Run agents"; Actual section |
| GET | `/api/events` | Structured audit events from `output/audit_trail.json` | query `ticket_id`, `run_id`, `agent`, `limit` (1–1000, default 200) | `EventList` {count, total_in_trail, events[] (agent, action, mcp_tool, tool_args, result_summary, outcome, approval_status, `approval_pending`, delegation source/target, stop_or_continue)} | Agent activity feed / timeline |
| GET | `/api/approvals` | Lists prepared payment and purchase actions | query `status`, `ticket_id` | `ActionList` {count, actions[] `PreparedAction`} | Pending-approvals panel |
| POST | `/api/approvals/{action_id}/approve` | Human approval: revalidates the action and cash through MCP, then executes a payment atomically, or records an approved purchase | path `action_id`; body `{approved_by, confirm: true}` | `ApproveResponse` {action (new status), executed, checking_balance, message}; 404 unknown, 409 stale / blocked / insufficient funds / already handled | "Approve" button on a pending action |
| GET | `/api/cash/checking` | Current checking balance via MCP `get_cash_account_balance` | — | `CashBalance` {account, balance, as_of, source} | Cash tab / balance display |
| POST | `/api/reset` | Copies `data/campus_customs.db` → `data/campus_customs_new.db` (never the reverse), and invalidates pending actions | body `{confirm: true}` | `ResetResponse` {reset, source, target, sha256, original_unchanged, invalidated_pending_actions, checking_balance} | "Reset demo data" button |

All errors share one JSON shape: `{"error": {"code", "message", "details"}}`.
- `400`: invalid input, including FastAPI validation errors, `confirm` not true, or a missing approver
- `404`: missing ticket, run, action, account or route
- `405`: wrong method, for example `GET /api/reset`
- `409`: stale, blocked, insufficient funds, already executed or approved, or a run in progress
- `503`: no `PORTKEY_API_KEY`
- `500`: unexpected failures only

### Permitted frontend origins (CORS)
- **Allowed origins:** `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`. These are explicit, with no wildcard. They can be overridden with the comma-separated `CORS_ORIGINS` environment variable.
- **Methods:** `GET`, `POST`, `OPTIONS`.
- **Headers:** `Content-Type`, `Accept`.
- **Credentials:** off.
- **Preflight:** succeeds (200) for allowed origins and is rejected (400) for any other origin.
- **Frontend configuration:** the dashboard should read the API base URL from configuration (for example `VITE_API_BASE_URL=http://localhost:8000`).

### Human-approval boundary
- **Agents can only prepare.** Runs register validated payment proposals, and restock purchase proposals, as `pending_human_approval` actions.
- **One route executes.** `POST /api/approvals/{action_id}/approve` is the **only** route that executes anything, and it requires `confirm: true` and a named human `approved_by`.
- **Single-execution guarantee:** under a lock, the route:
  1. checks the action exists and is still pending;
  2. re-runs `check_payment_feasibility` through MCP, refusing a mismatched amount as `stale` and a blocked or insufficient-funds check as `409`;
  3. atomically claims the action (`pending` → `executing`), so it can't run twice;
  4. calls MCP `execute_approved_payment` with `expected_amount`. That tool rechecks everything in one `BEGIN IMMEDIATE` transaction, with `UPDATE ... WHERE balance >= amount`, so a negative balance is impossible.
- **Repeat approvals** return `409` (`action_executed` / `action_approved`).
- **Purchases are never executed by the system.** Approval records the decision, but placing the order means contacting a vendor, which a human must do.
- **Audited:** every decision is written to `output/audit_trail.json`.

### Verification (performed against the running server on port 8000)
- **Read routes:** `/api/health`, `/api/tickets` (101, 102, 103, all `is_open: true`), `/api/cash/checking` (3400.0), `/api/events` and `/api/approvals` returned 200 JSON. `/docs` loaded.
- **CORS:** preflight from `localhost:5173` and `localhost:3000` returned 200 with the matching `access-control-allow-origin`. A disallowed origin got 400.
- **Errors:**
  - ticket 999 → 404; `abc` → 400; `0` → 400
  - unknown action → 404; `confirm: false` → 400; missing body → 400
  - unknown run → 404; `GET /api/reset` → 405
  - run with no API key → 503
- **Controlled approval test** on the working copy, using test actions built from real feasibility values:
  - stale amount → 409 `action_stale`
  - rent $2,400 executed → balance 1000.0
  - same action again → 409 `action_executed`
  - the next month's rent ($2,400 against a $1,000 balance) → 409 `insufficient_funds`, balance unchanged
  - a purchase → 200 `approved`, `executed: false`; again → 409
- **Reset:** `POST /api/reset` then restored the working copy, byte-identical to the original. The original's hash and mtime were unchanged.
- **Cleanup:** the test-only `pending_actions.json` was removed. The audit trail keeps the test entries as a truthful record.
- **Not tested:** no agent run was performed, because `PORTKEY_API_KEY` is not set.

---

## Final System Reference (Problem 9)

This section describes the system exactly as implemented after Problem 9. Facts were taken from the code (`mcp_server/server.py`, `backend/agents.py`, `backend/config.py`, `backend/main.py`, `frontend/src/`) and the live OpenAPI schema.

### 1. Database tables and why they matter

| Table | Key fields | Why it matters to the agents | Reached through (MCP tools) |
|---|---|---|---|
| `desk` | `date_today`, `notes` | The shop's "today" (2026-08-31). Every due, overdue and arrival calculation uses it, never the computer clock | `get_shop_date`, plus inside `get_invoice_with_vendor`, `get_vendor_shipping_status`, `check_payment_feasibility`, `execute_approved_payment` |
| `inventory` | PK (`sku`, `size`), `name`, `qty`, `location` | Stock on hand per SKU and size (101: tee S = 0; 103: hoodie M = 8) | `get_inventory_stock_for_sku_size` |
| `pricing` | PK `sku`, `unit_cost`, `list_price` | Cost and list price bound any discount (103: $22 / $58) and support customer drafts | `get_sku_cost_and_list_price` |
| `vendors` | PK `id`, `name`, `specialty`, `lead_days` | Who can restock and how fast. There is no SKU-to-vendor link, so a specialty match is always labelled an inference | `list_vendors`, `get_vendor_shipping_status`, `get_invoice_with_vendor` |
| `invoices` | PK `id`, FK `vendor_id`, `amount`, `due_date`, `status` | Vendor debts. An open unpaid invoice blocks that vendor from shipping (invoice 501 blocked ticket 101) | `get_invoice_with_vendor`, `get_vendor_shipping_status`, `check_payment_feasibility`, `execute_approved_payment` (writes `status='paid'`) |
| `leases` | PK `id`, `space_name`, `landlord`, `monthly_rent`, `next_due` | The rent obligation behind ticket 102 | `get_lease_rent_and_cash_balance`, `check_payment_feasibility`, `execute_approved_payment` (advances `next_due` one month) |
| `cash_accounts` | PK `name`, `balance`, `date` | The only source of cash. Payments are refused if they would make it negative | `list_cash_accounts`, `get_cash_account_balance`, `get_lease_rent_and_cash_balance`, `check_payment_feasibility`, `execute_approved_payment` (decrements) |
| `payments` | PK `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by` | The ledger of human-approved payments. It prevents double payment and shows rent already paid | `get_invoice_with_vendor`, `get_lease_rent_and_cash_balance`, `check_payment_feasibility`, `execute_approved_payment` (inserts) |
| `tickets` | PK `id`, `type`, `requester`, `sku`/`size`/`qty`, FK `lease_id`, FK `invoice_id`, `status` | The work queue. `status` becomes `resolved` only through a human-approved resolution | `list_tickets`, `list_open_tickets`, `get_ticket_details`, `resolve_ticket` (writes `status='resolved'`) |

### 2. MCP tools (15), their tables, and who may use them

All tools live in `mcp_server/server.py` (FastMCP, stdio). They use **only `data/campus_customs_new.db`**, and every query is parameterized. Read-only tools open the database with `mode=ro`, and a missing database file raises an error rather than being created. There is no general SQL or update tool.

| Tool | Tables (R = read, W = write) | Agents allowed | Ticket need |
|---|---|---|---|
| `get_shop_date` | desk R | all five | All tickets: the shop's current date |
| `list_open_tickets` | tickets R | Boss | Routing the open tickets |
| `get_ticket_details` | tickets R | all five | Exact request, linked `invoice_id` / `lease_id` |
| `list_tickets` | tickets R | none (dashboard API) | Ticket list with open/resolved status |
| `get_inventory_stock_for_sku_size` | inventory R | Inventory, Customer Service | 101 tee S stock; 103 hoodie M stock |
| `get_sku_cost_and_list_price` | pricing R | Inventory, Customer Service | 103 discount bounds; 101 price for the draft |
| `list_vendors` | vendors R | Inventory | 101/103 possible restock source (inference) |
| `get_vendor_shipping_status` | vendors, invoices, desk R | Inventory | 101/103 vendor blocker rule and arrival date |
| `get_invoice_with_vendor` | invoices, vendors, payments, desk R | Accounting | 101 invoice 501 status, past-due flag, payments |
| `get_lease_rent_and_cash_balance` | leases, cash_accounts, payments R | Accounting, Facilities | 102 rent obligation, balance, and `recorded_rent_payments` |
| `list_cash_accounts` | cash_accounts R | Accounting, Facilities | Real account name; never guess |
| `get_cash_account_balance` | cash_accounts R | none (dashboard API, approval path) | Header balance; post-approval balance |
| `check_payment_feasibility` | invoices, vendors, leases, payments, cash_accounts, desk R | Accounting | 101/102: amount from the database, blockers, balance after, decision |
| `execute_approved_payment` | payments W, cash_accounts W, invoices W / leases W; vendors, desk R | **none: human-only** | Executes one approved payment |
| `resolve_ticket` | tickets W | **none: human-only** | Marks one open ticket resolved after human approval |

Human-only tools are excluded from every agent's allow-list (`ALLOWED_TOOLS`), listed in `HUMAN_ONLY_TOOLS`, and refused by the MCP call hook even if requested. Only `backend/orchestrator.approve_action` calls them, and that is reached only through `POST /api/approvals/{action_id}/approve`.

### 3. The five agents and their scopes

Every agent is a PydanticAI agent on **`gpt-6-luna` through Portkey**. It uses the OpenAI Responses API via `OpenAIResponsesModel`, because this deployment rejects function tools on `/chat/completions`. The key is read from the `PORTKEY_API_KEY` environment variable and sent only as the `x-portkey-api-key` header. Prompts are in `backend/prompts/*.md`; shared models are in `backend/models.py`.

| Agent | Scope | Outside scope | Output |
|---|---|---|---|
| **Boss** | Reads tickets and the shop date, delegates, combines results, tracks success / partial / blocked / failed / needs-approval, and reports `succeeded` only when MCP evidence shows the work is done | Specialist work, payments, messages, record changes | `BossReport` (one `TicketOutcome` per ticket) |
| **Inventory** | Stock, pricing, vendors, lead times, vendor shipping blockers, restock proposals | Invoices or cash, leases, customer wording, placing orders | `AgentResult` |
| **Accounting** | Invoices, cash accounts (via `list_cash_accounts`), feasibility checks, payment proposals that exactly match a feasibility result | Executing payments, inventory, leases beyond rent | `AgentResult` with `PaymentProposal`s |
| **Facilities** | Leases, landlord, rent due dates, recorded rent payments, verifying notices | Paying rent, contacting the landlord, changing leases | `AgentResult` |
| **Customer Service** | Customer-ticket analysis and internal `CustomerDraft`s (`sent: false`) | Sending anything, promising outcomes, discounts | `AgentResult` |

### 4. Delegation behavior
- **Full connectivity, structured requests.** Every agent has `delegate_task(DelegationRequest{target_agent, ticket_id, task, known_facts})` and can reach any other agent. The code, not the model, fills in the source and depth.
- **Results flow back up.** The target returns a structured `AgentResult` to its caller. The Boss is the root of every dashboard run, so results always come back to it.
- **Limits enforced in code:**
  - depth at most **3**
  - at most **12** delegations per run
  - no self-delegation
  - no delegation to an agent already in the chain (prevents cycles)

  Refusals return a `blocked` result with `ErrorCode.delegation_limit` and are audited.
- **Observed in Problem 9:**
  - The Boss often delegated to two specialists in parallel.
  - Depth-2 hand-offs happened: Facilities → Accounting (102) and Customer Service → Inventory (101).
  - No refusals occurred in the clean run. An earlier Problem 8 run showed the cycle guard refusing Inventory → Boss.

### 5. FastAPI routes (`backend/main.py`, `uvicorn main:app --reload --port 8000` from `backend/`)

| Method | URL | Purpose | Dashboard caller |
|---|---|---|---|
| GET | `/api/health` | DB files present, MCP reachable, model key configured (yes/no), shop date | Header connection pill |
| GET | `/api/tickets` | All tickets via MCP `list_tickets`, with `is_open` | Ticket navigation and badges |
| POST | `/api/tickets/{ticket_id}/run` | Validates the ticket (400 / 404 / 409 / 503) and starts the Boss in the background; returns 202 `RunStatus` | "Run agent team" |
| GET | `/api/runs/{run_id}` | Run status and `BossReport` (kept in memory for this server session) | Run polling and summary |
| GET | `/api/events` | Audit events, filterable by `ticket_id`, `run_id`, `agent`, `limit` | Agent activity feed and badges |
| GET | `/api/approvals` | Prepared actions (payment / purchase / ticket_resolution) | Approval cards and history |
| POST | `/api/approvals/{action_id}/approve` | Human approval (body `{approved_by, confirm: true}`) | "Review & approve…" → confirm |
| GET | `/api/cash/checking` | Balance via MCP `get_cash_account_balance` | Header balance |
| POST | `/api/reset` | Copies original → working, invalidates pending actions (body `{confirm: true}`) | Maintenance → Reset |

- **Error format:** `{"error": {code, message, details}}`, with 400 / 404 / 405 / 409 / 503, and 500 only for unexpected failures.
- **CORS:** explicit origins `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`. Methods GET / POST / OPTIONS; headers Content-Type and Accept.

### 6. React dashboard behavior (`frontend/`, `npm run dev`, port 5173)
- **Talks to the backend through one client.** `src/api/client.ts` reads `VITE_API_BASE_URL` (default `http://localhost:8000`), and `src/api/types.ts` mirrors the backend models. Nothing is hardcoded or simulated.
- **Ticket tabs:** keyboard-accessible (arrow keys, Home, End). `?ticket=ID` selects a ticket.
- **Status badges:**
  - Open, Running, Approval needed, Blocked, Run failed come from runs, actions and the audit trail.
  - **Resolved appears only when the backend's `tickets.status` is `resolved`.**
- **Running a ticket:** the Run button is disabled while that ticket runs. The UI polls the run every 2 s and the event feed every 2 s while live.
- **Activity feed:** shows each agent in its own color and icon, with delegations, MCP calls and results, refusals, and conclusions. It shows structured events only, never hidden reasoning.
- **Run summary:** the Boss's conclusion, blockers, decisions for a human, a per-agent digest built from events, and customer drafts marked "Not sent".
- **Approval cards:** a two-step deliberate approval (review, then confirm with the approver's name). A synchronous guard prevents a double submit. The card shows the backend's exact result: executed, approved, resolved, blocked, insufficient funds, stale, or duplicate.
- **Cash:** read only from the backend, never changed locally. It refreshes after approvals, resets and finished runs.
- **Reset:** a separate Maintenance control with a confirmation dialog.

### 7. Human-approval workflow
1. An agent run registers actions in `output/pending_actions.json` (`backend/actions.py`) as `pending_human_approval`:
   - **payment:** only `PaymentProposal`s that passed validation against a `check_payment_feasibility` result;
   - **purchase:** `restock_order` proposals with status `proposed`;
   - **ticket_resolution:** created when the Boss reports `succeeded` with no blockers and no human decisions.

   Identical pending actions are de-duplicated.
2. A human opens the card, enters their name and confirms. The UI sends `POST /api/approvals/{id}/approve` with `{approved_by, confirm: true}`.
3. Under a lock, the backend checks that the action exists and is still pending. Anything else returns 404 or 409 (`action_executed`, `action_approved`, `action_stale`, `action_blocked`, `insufficient_funds`).
4. **Payment:**
   1. re-run `check_payment_feasibility`; a changed amount marks the action `stale`, and a blocked or insufficient check returns 409;
   2. atomically claim the action (`pending` → `executing`);
   3. call `execute_approved_payment` with `expected_amount`, which rechecks everything inside `BEGIN IMMEDIATE`;
   4. on success, store `payment_id` and the balance.

   **Purchase:** recorded as `approved` only. The system never contacts vendors.

   **Ticket resolution:** claim the action, then call `resolve_ticket`.
5. Each decision and MCP execution is audited.

In Problem 9, the human (Lee Itzhaki) approved 2 payments and 1 resolution, and left 1 purchase pending. Each was approved in chat before the dashboard control was used.

### 8. Audit logging
- **Where:** `output/audit_trail.json` is an append-only JSON array (`backend/audit.py`). Each append re-reads the file under a file lock and atomically replaces it. A corrupt file is never overwritten.
- **Fields:** timestamp, run ID, step, event, agent, ticket ID, action, delegation source / target / depth, MCP tool, redacted tool arguments, short result summary, approval status, outcome, error, and stop/continue reason.
- **Events recorded:** run start and finish, every MCP call, delegations and their returns, refusals, limits, approval requests and decisions, API run requests, and database resets.
- **Run IDs:** each agent run has a distinct 12-hex run ID. Approval executions use `approval_*`, and resets use `api`.
- **Not recorded:** API keys, credentials, prompts and hidden reasoning. Secret-looking keys and values are redacted.

### 9. Database reset behavior
`POST /api/reset` (dashboard: Maintenance → Reset, with a confirmation dialog) does the following:
1. Requires `{confirm: true}`.
2. Refuses while a run is in progress, and holds the approval lock so no approval can execute meanwhile.
3. Hashes the original file.
4. Restarts the MCP gateway so no SQLite handles stay open.
5. Copies `data/campus_customs.db` → a temp file, then runs `PRAGMA integrity_check`.
6. Removes any stale `-wal` / `-shm` / `-journal` files, then atomically replaces `data/campus_customs_new.db`.
7. Verifies the working hash equals the original's and that the original is unchanged.
8. Marks pending actions `stale` and audits the reset.

**The copy only ever runs from the original to the working copy, never the reverse.**

### 10. Safety rules
- **Payments need a human.** Agents prepare; only the approval route executes, and human-only tools are blocked for agents in three places (allow-list, `HUMAN_ONLY_TOOLS`, call hook). Validators reject agent outputs that claim approval or execution.
- **No contact.** No customer or vendor contact capability exists. Drafts are typed `sent: false`, and purchases are recorded, never placed.
- **No invented facts.** Every `Evidence` item must cite an MCP tool actually called in the run, and payment proposals must exactly equal a feasibility result. Lookups return explicit `found: false` instead of guesses.
- **MCP-only access.** The backend has no direct SQL for shop data (the reset is a file copy). The frontend never touches SQLite.
- **Shop rules in code:** `desk.date_today` is the date, lead times come from `vendors.lead_days`, an open unpaid invoice blocks shipping, amounts come from the database, and no revenue or inflow is ever assumed.
- **Keys.** `PORTKEY_API_KEY` exists only in the environment. It is never in code, prompts, outputs or the audit trail (checked by scanning `output/`).

### 11. Insufficient-funds and negative-balance protections
- **At preparation:** `check_payment_feasibility` returns `decision: "blocked"` with an "Insufficient funds…" blocker whenever `balance − amount < 0`. A proposal built on it must be `blocked`, and only `proposed` ones become approval cards.
- **At approval:** the route re-runs the check immediately before executing. Insufficient funds return 409 `insufficient_funds`, and nothing executes.
- **At execution:** inside one `BEGIN IMMEDIATE` transaction, `UPDATE cash_accounts SET balance = balance - ? WHERE name = ? AND balance >= ?` must touch exactly one row. A defensive check rolls back if the balance is negative.
- **Observed in Problem 9:** after rent was paid (balance $160.00), Accounting's feasibility checks for another rent payment came back blocked (balance would be −$2,240.00), and no proposal was created.

### 12. Token, tool-call and agent-step limits (`backend/config.py`)

| Limit | Value |
|---|---|
| Delegation depth | 3 |
| Delegations per run | 12 |
| Audited steps per run | 80 |
| Failed / not-found MCP results before the hook stops a run | 4 |
| Output-validation retries per agent | 2 |
| Retries per failed MCP tool | 1 |
| Model requests per run (shared by all agents) | 40 |
| Tool calls per run (shared) | 60 |
| Total tokens per run (shared) | 250,000 |

Exceeding a usage limit stops the run with a `limit_reached` audit entry. Refused delegations, missing data and approval blockers end as `blocked` / `needs_human_approval` and are never reported as success.

### 13. Problem 9 run record

**Reset:** at 2026-10-11T23:49:16Z through the dashboard (audit entry index 149). The working copy was byte-identical to the original, which stayed unchanged. Starting checking balance: **$3,400.00**.

| Ticket | Runs | Final status | Cash change | Checking after |
|---|---|---|---|---|
| 101 | `c8f8c9868cee`, `bba1e8dc9149` | open | −$840.00 (payment #1, invoice 501) | $2,560.00 |
| 102 | `43c4e15e7d5f`, `7c234e6f28d9`, `cee1873a1426` | **resolved** | −$2,400.00 (payment #2, lease 1 rent) | $160.00 |
| 103 | `871e6f7e7375` | open | $0.00 | $160.00 |

- **Fixes made during Problem 9** (each the smallest change for an observed problem):
  - **`list_cash_accounts` (MCP, read-only):** Accounting, and later Facilities, had been guessing account names.
  - **Human-approved ticket resolution** (`resolve_ticket` plus `ticket_resolution` actions): nothing could change `tickets.status` before.
  - **`recorded_rent_payments` in `get_lease_rent_and_cash_balance`:** run `7c234e6f28d9` misread the advanced `next_due` as a conflict.
  - **Dashboard:** `?ticket=` deep link, summary fallback to the recorded Boss conclusion, and approval history sorted newest-first.
- **Abandoned first attempt:** runs `b9ad86ce2264`, `68379540948a`, `3b4d4e1eb9a9` and a dashboard-started `49e5e420bb2a`. It was abandoned when the human asked to reverse its approvals. The database was reset, and the clean run above began. Those events remain in the audit trail before index 149.
- **Detailed evidence:** `output/resolved_tickets.json`, the Actual and Cash tabs of `output/desk_tickets.html`, and screenshots in `output/resolved_board.html`.
