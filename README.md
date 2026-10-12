# Campus Customs: Multi-Agent Operations Desk (HW5)

A team of five PydanticAI agents works a campus apparel shop's open tickets. All shop facts come from a FastMCP server over a SQLite database. A FastAPI backend runs the team and enforces human approval for anything that moves money or closes a ticket, and a React dashboard lets a person watch the agents and make those decisions.

```
React dashboard (frontend/, :5173)
        │  JSON over HTTP (CORS: localhost:5173 / :3000)
        ▼
FastAPI backend (backend/main.py, :8000) ──► output/audit_trail.json, output/pending_actions.json
        │  runs the agent team (backend/agents.py, backend/orchestrator.py)
        ▼
Boss ⇄ Inventory ⇄ Accounting ⇄ Facilities ⇄ Customer Service   (PydanticAI, gpt-6-luna via Portkey)
        │  MCP tool calls only (stdio)
        ▼
FastMCP server (mcp_server/server.py) ──► data/campus_customs_new.db (working copy)
                                          data/campus_customs.db     (original, never modified)
```

## The five agents

Prompts are in `backend/prompts/`, and the shared Pydantic models are in `backend/models.py`.

| Agent | Prompt | Responsibility |
|---|---|---|
| **Boss** | `boss.md` | Reads tickets and the shop date, delegates to specialists, combines their results, and reports each ticket's outcome. Never does specialist work or claims a resolution nobody produced. |
| **Inventory** | `inventory.md` | Stock by SKU and size, cost and list price, vendors, lead times, vendor shipping blockers, restock proposals. |
| **Accounting** | `accounting.md` | Invoices, cash accounts, payment-feasibility checks, payment proposals. Can never execute a payment. |
| **Facilities** | `facilities.md` | Leases, landlord, rent due dates, recorded rent payments; verifies notices against the lease. |
| **Customer Service** | `customer_service.md` | Customer-ticket analysis and internal reply drafts, which are never sent. |

- **One model:** every agent uses **`gpt-6-luna`** through the Portkey gateway (OpenAI Responses API), configured in `backend/config.py`.
- **Delegation:** agents can delegate to one another with a structured `delegate_task` tool. The code caps it at depth 3, 12 delegations per run, no cycles, and a shared token and tool budget.
- **Least privilege:** each agent sees only the MCP tools it needs.

## Requirements

- **macOS or Linux.** The backend uses `fcntl` file locks; on Windows, use WSL.
- **Python 3.11 or newer.** Built and verified with Python 3.14.7.
- **Node.js 20.19 or newer, with npm.** Built with Node 24.20.0 and npm 11.19.0.
- **A Portkey API key** with access to `gpt-6-luna`.

## Setup

Run these from the repository root.

**1. Python dependencies.** The virtual environment must be at `.venv/`, because `.mcp.json` and `backend/config.py` use `.venv/bin/python`.

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

**2. Frontend dependencies.**

```bash
cd frontend && npm install && cd ..
```

**3. Environment.** Create your local `.env` from the template, then edit `.env` and set `PORTKEY_API_KEY=<your key>`.

```bash
cp .env.example .env
```

- **Required:** `PORTKEY_API_KEY`. It is read from the environment or from `.env`, and is never written to code, logs or outputs. `.env` is git-ignored.
- **Optional:** `PORTKEY_BASE_URL` (default `https://api.portkey.ai/v1`), `PORTKEY_PROVIDER` (default `openai`) and `CORS_ORIGINS`.
- **Frontend:** the base URL is `VITE_API_BASE_URL` (default `http://localhost:8000`). To change it, copy `frontend/.env.example` to `frontend/.env`.

**4. Working database.** `data/campus_customs.db` is the clean original and is never modified. All work happens in `data/campus_customs_new.db`. To start from a clean working copy, do one of the following:
- copy the file by hand while the backend is stopped:

  ```bash
  cp data/campus_customs.db data/campus_customs_new.db
  ```

- or use the dashboard's **Maintenance → Reset working database…** control, or `POST /api/reset`, while the backend is running. See "Reset" below.

## Running

**MCP server.** There is nothing to start by hand. The backend launches `mcp_server/server.py` over stdio for every agent run and for its own lookups. It always uses `data/campus_customs_new.db`. To use the same server from Claude Code, the project's `.mcp.json` registers it as `campus-customs` (command `.venv/bin/python mcp_server/server.py`). To check that it starts on its own (it then waits on stdio; stop it with Ctrl-C):

```bash
.venv/bin/python mcp_server/server.py
```

**FastAPI backend** (terminal 1):

```bash
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000
```

If the virtual environment is activated, `uvicorn main:app --reload --port 8000` works the same from inside `backend/`. API docs are at http://localhost:8000/docs, and http://localhost:8000/api/health should show `"model_configured": true`.

**React frontend** (terminal 2), then open http://localhost:5173:

```bash
cd frontend && npm run dev
```

## The three-ticket workflow

1. **Reset first.** In the dashboard's left column, under **Maintenance**, click **Reset working database…** and confirm. The checking balance should read **$3,400.00** and tickets 101, 102 and 103 should show **Open**.
2. **Run each ticket in order: 101, then 102, then 103.** Select the ticket, click **Run agent team**, and watch **Agent activity**: each agent's delegations, MCP tool calls and results, live. When the run finishes, the **Run summary** shows the Boss's conclusion, blockers and what each agent did.
3. **Approve only through the dashboard.** When an agent prepares a payment, purchase or ticket resolution, an amber **Human approval needed** card appears:
   1. click **Review & approve…**;
   2. read the confirmation text and type your name;
   3. click **Confirm & pay $…**, **Confirm approval** or **Confirm: mark resolved**.

   The backend rechecks the action and the cash first, refuses stale, duplicate or insufficient-funds requests, and never lets the balance go negative. Purchases are recorded only; the system never contacts vendors or customers.
4. **Re-run after an approval if needed.** After approving a payment, run the ticket again so the agents can verify the new state. If the Boss reports the ticket complete, a **Resolve ticket** card appears for your approval.

### Outcomes of the recorded run (Problem 9)

| Ticket | Final status | Why |
|---|---|---|
| 101: Bulldog tee, size S | **open** | Invoice 501 ($840.00) was paid with approval, which unblocked the vendor. But the shirt is still out of stock, the restock purchase was not approved, and the system cannot place or verify an external replenishment order. |
| 102: Rent due | **resolved** | Rent of $2,400.00 was paid with approval. The agents verified the payment, and the resolution was approved. |
| 103: Bulk hoodie discount | **open** | No approved bulk-discount policy exists, only 8 of the 20 hoodies are available, and the system cannot authorize a discount or replenish the other 12. |

Checking went from $3,400.00 to **$160.00**: two approved payments totaling $3,240.00. These open statuses are accurate outcomes, not failures. The agents stopped when data, authority or external capabilities were missing.

## Reset

`POST /api/reset` (the dashboard's Maintenance control) copies the original over the working copy, never the reverse. It refuses while a run is in progress, checks integrity and hashes, and marks any pending approvals stale. The audit trail is kept.

## Where things are stored

| Path | Contents |
|---|---|
| `output/audit_trail.json` | Append-only structured audit of every run, MCP call, delegation, approval and reset. No keys and no hidden reasoning. |
| `output/pending_actions.json` | Prepared and decided actions (payments, purchases, resolutions) |
| `output/resolved_tickets.json` | Final per-ticket results from the Problem 9 run |
| `output/desk_tickets.html` | Expected plans, the actual results, the cash reconciliation and the reflection (tabs) |
| `output/resolved_board.html` | Real dashboard screenshots for each ticket (`output/resolved_ticket_10{1,2,3}.png`) |
| `output/harness.md` | Full documentation: tables, MCP tools, agents, routes, safety rules and limits |
| `output/design.md` | Dashboard design notes |
| `output/mcp_smoke.json` | MCP smoke-test evidence (Problem 4) |
| `AI_prompts.md` | The prompts used for Problems 2–10 |

**Opening the HTML evidence.** Both pages are self-contained, so you can double-click them or run:

```bash
open output/desk_tickets.html
```

```bash
open output/resolved_board.html
```

On Linux, use `xdg-open` instead of `open`.

## API routes (`backend/main.py`)

| Method | Route |
|---|---|
| GET | `/api/health` |
| GET | `/api/tickets` |
| POST | `/api/tickets/{ticket_id}/run` |
| GET | `/api/runs/{run_id}` |
| GET | `/api/events?ticket_id=&run_id=&agent=&limit=` |
| GET | `/api/approvals` |
| POST | `/api/approvals/{action_id}/approve` (body `{"approved_by": "...", "confirm": true}`) |
| GET | `/api/cash/checking` |
| POST | `/api/reset` (body `{"confirm": true}`) |

See `output/harness.md` for details.
