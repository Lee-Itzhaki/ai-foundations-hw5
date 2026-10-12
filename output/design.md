# Campus Customs Operations Desk: Dashboard Design

The dashboard lives in `frontend/`, built with React 19, Vite and TypeScript. Start it from `frontend/` with `npm run dev`; it serves at `http://localhost:5173`. It is a working desk for one person: pick a ticket, send the agent team to work on it, watch what they do, and make the decisions only a human may make.

## Layout

```
┌──────────────────────────────── Masthead ─────────────────────────────────┐
│ CC crest · Campus Customs Operations Desk · shop date · model              │
│                      backend status · "N awaiting approval" · CHECKING $ · Refresh │
├───────────────┬───────────────────────────────────┬───────────────────────┤
│ DESK TICKETS  │ Selected ticket                   │ Agent activity        │
│ #101  [badge] │  subject, requester, notes, fields│  agent roster (5)     │
│ #102  [badge] │  Run agent team ─ run state       │  live event feed      │
│ #103  [badge] ├───────────────────────────────────┤  (delegations,       │
│               │ Human approval needed  (only when │   MCP tool calls,     │
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄ │  something is pending)            │   outcomes)           │
│ MAINTENANCE   ├───────────────────────────────────┤                       │
│ Reset working │ Run summary: Boss conclusion,     │                       │
│ database…     │  blockers, decisions, per agent   │                       │
└───────────────┴───────────────────────────────────┴───────────────────────┘
```

- **Masthead:** the operator's constant context. It shows whether the backend is reachable, how many actions are waiting for them, and the real checking balance.
- **Ticket navigation (left):** three cards, one per ticket, each with a status badge. They are a vertical tab list, so arrow keys, Home and End move between tickets.
- **Workspace (centre):** everything about the selected ticket, from top to bottom:
  1. the ticket itself and the **Run agent team** button;
  2. the approval area, which appears only when the agents prepared something;
  3. the run summary.
- **Agent activity (right):** a sticky column, so the live feed stays visible while you read the summary. Below 1180px wide it moves under the workspace. Below 760px everything stacks.
- **Maintenance (left, below the tickets):** the **Reset working database** control sits apart from the everyday workflow. It has a dashed, muted container, so it is never confused with a normal action.

## Visual style and colors

- **Palette:** deep **Yale blue** `#00356B` (masthead, primary buttons, ticket numbers, selected ticket) on a **warm paper** background `#F6F3EC`, with white cards and a thin **antique-gold** rule `#B88A3B` under the masthead.
- **Gold:** also used for the keyboard focus ring and the cash-change highlight.
- **Type:** headings use a classic serif (Iowan Old Style, Palatino or Georgia, all system fonts) for a collegiate, printed-ledger feel. Body text uses the system sans-serif for readability, and tool names and JSON use a monospace font.
- **The crest:** a white shield with "CC" on the masthead (also the favicon) gives the desk a Yale identity without copying Yale marks.
- **Status colors:** one consistent set, each meeting WCAG AA contrast on its tint.

| State | Text / tint | Used for |
|---|---|---|
| Info | `#1F5FA8` on `#E5EEF8` | Running, approved-not-executed |
| Approval | `#9A5B00` on `#FCF0D8` | Approval needed, partial |
| Blocked / failed | `#B42318` on `#FCE8E6` | Blocked, insufficient funds, run errors |
| Success | `#2E7D4F` on `#E5F3EA` | Executed, resolved |
| Neutral | `#4A4F5A` on `#EDEBE6` | Stale, duplicate, closed history |

- **No external services:** no web fonts, icon CDNs or analytics. Everything ships with the app.

## How the five agents are distinguished

Each agent has the same **name, line-icon and accent color** wherever it appears: roster, feed rows, tags and summary cards. The colors are chosen to stay distinct from the status colors.

| Agent | Icon | Accent |
|---|---|---|
| Boss | compass (sets direction) | Yale blue `#00356B` |
| Inventory | box | forest green `#2D6A4F` |
| Accounting | ledger | bronze `#8A5300` |
| Facilities | storefront | violet `#5B4699` |
| Customer Service | speech bubble | raspberry `#A3324F` |

- **Roster:** sits at the top of the activity column. Agents not involved in the current run are dimmed. Agents that took part say "took part". During a live run, the agent that acted last is outlined and says "working…".
- **Feed rows:** each row has a left rule in the acting agent's color, a faint tint and its avatar.
- **Non-agent actors:** human approval decisions use a neutral "Human approver" identity, and backend requests use "Desk system", so you can always tell who acted.
- **Only operational events are shown:** delegations ("Delegated to Facilities", "Reported back to Boss"), MCP calls (`get_lease_rent_and_cash_balance(lease_id=1, …)` plus the returned fields), refusals, approvals and conclusions. These all come from the audit trail; no hidden reasoning is displayed.

## How ticket states appear

Each ticket card and the ticket header carry one badge:

| Badge | Look | Meaning (from backend data) |
|---|---|---|
| **Open** | blue outline on pale blue | The database says `open`, and there's nothing pending, running or blocked |
| **Running** | blue with a pulsing dot | A run for this ticket is in progress (`GET /api/runs/{id}` says `running`) |
| **Approval needed** | amber | A prepared action is `pending_human_approval`, or the Boss's latest outcome needs a human and nobody has decided since |
| **Blocked** / **Run failed** | red | The Boss concluded `blocked`, or the run errored (for example a model or gateway error) |
| **Resolved** | green | Only when `GET /api/tickets` returns `is_open: false`. The UI never marks a ticket resolved by itself |

- **During a run,** the ticket's button changes to a disabled "Running…". The feed gets a red **LIVE** marker and refreshes every 2 seconds. Reset is disabled until the run finishes.
- **After a run,** the summary shows the Boss's conclusion in a tinted panel (green, amber or red by status), then blockers, decisions for a human, a card per participating agent (what it reported, which MCP tools it used, who it delegated to), and any customer drafts, labelled **Not sent**.

## Cash and approval requests

- **Checking balance** sits in a white plate in the masthead, formatted as US currency with its as-of date.
- **The balance is only ever what `GET /api/cash/checking` returns.** It is re-read after every approval, after a reset, when a run finishes, and every 30 seconds. When the value changes, the plate briefly glows gold so the operator notices. The UI never subtracts anything locally.
- **Approval cards** appear in an amber-bordered panel titled **Human approval needed (n)**, and a matching chip appears in the masthead. Each card shows:
  - the action type (rent payment, vendor invoice payment or purchase);
  - the amount, as a large figure, and the payee;
  - the purpose and the related ticket;
  - the source account and the balance-after figure at preparation time;
  - which agent prepared it and when;
  - its current status.
- **Approving takes two deliberate steps.** First **Review & approve…** opens a confirmation box. It explains exactly what will happen ("This will execute a real payment of $2,400.00 from checking…") and asks for the approver's name. Then **Confirm & pay $2,400.00** submits. The button disables immediately, protected by a synchronous guard, so a double-click can't send two requests.
- **The result shows exactly what the backend said:**
  - Executed (green)
  - Approved, not executed (blue, for purchases, because the system never contacts vendors)
  - Insufficient funds, Blocked (red)
  - Stale, Duplicate (neutral), each with the backend's message
- **Closed actions** move into a collapsible **Approval history**. If the working database was reset after a payment, its card says the payment's effect has been undone.

## How the dashboard talks to the backend

- **One API client:** `src/api/client.ts` is the only place that calls `fetch`. Its base URL comes from `VITE_API_BASE_URL` and defaults to `http://localhost:8000` (see `frontend/.env.example`). No other file contains the URL.
- **Typed contracts:** `src/api/types.ts` mirrors the FastAPI response models in `backend/main.py`, `backend/models.py` and `backend/actions.py`. Backend errors (`{"error": {code, message, details}}`) become a typed `ApiError`, and the UI shows the human-readable `message`.
- **Routes and polling:**
  - `GET /api/health`: every 10 s
  - `GET /api/tickets`: every 15 s, every 4 s during a run
  - `POST /api/tickets/{id}/run`, then `GET /api/runs/{run_id}` every 2 s until it finishes
  - `GET /api/events?run_id=…` or `?ticket_id=…`: every 2 s while live; `?limit=1000` for badges and summaries
  - `GET /api/approvals`: every 4 s while anything is pending or running
  - `POST /api/approvals/{id}/approve` with `{approved_by, confirm: true}`
  - `GET /api/cash/checking`
  - `POST /api/reset` with `{confirm: true}`
- **Recovery:** when the backend comes back after being unreachable, the dashboard reloads everything at once. A red banner explains how to start the backend while it is down.
- **CORS:** the backend explicitly allows `http://localhost:5173`, so preflights for the POST routes succeed. No database file is ever touched from the browser.

## Choices that make it pleasant and practical

- **Calm by default, loud only when needed.** The approval area doesn't exist until there is something to approve. Then it takes amber borders and a masthead chip.
- **Errors say what to do.** For example, "Can't reach the backend… start it from `backend/` with `uvicorn main:app --reload --port 8000`", or the model gateway's exact rejection message when a run fails. Every error panel has a **Retry** button.
- **Honest summaries.** Outcomes come from the Boss's structured report and the audit trail. A conflicting or partial result is shown as such, never smoothed into "success".
- **Remembers context.** The selected ticket and the approver's name are kept in local storage. A run in progress is resumed after a page reload.
- **Keyboard and screen readers:**
  - a skip link;
  - semantic headings;
  - ARIA tabs for tickets;
  - `aria-live` regions for the connection, cash and live feed;
  - a native `<dialog>` for the reset confirmation;
  - a visible gold focus ring on every control.
- **Readable at laptop widths.** Verified at 1440×900 and 1280×800 with no horizontal overflow; long JSON tool results wrap inside their rows.
