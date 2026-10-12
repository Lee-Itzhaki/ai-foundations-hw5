# HW5 — AI Prompts Log

> **About this file**
>
> - This is a chronological record of the prompts used with the coding assistant while completing Problems 2–10.
> - Only prompts that were actually used are included.
> - Follow-up prompts appear only when one was genuinely needed.
> - Assignment page URLs and screenshots are not substituted for prompts; every prompt below is written in my own words.

---

## Problem 2 — Database Analysis and Harness

### Prompt

```text
Let’s work only on Problem 2.
Inspect the Campus Customs SQLite database `campus_customs.db` and the working copy at campus_customs_new.db in the data folder I just created in the root folder. Verify that both files exist and that the working copy matches the original, but do not overwrite or modify either database during this problem.
Analyze every table in the database. For each table, identify:

* Its fields/columns
* Data types
* Primary and foreign keys
* Important relationships with other tables
* A short explanation of why that table matters to the agents, including which agent or agents are likely to rely on it when supported by the database structure

Study the three open tickets and trace how each ticket connects to relevant records in the other tables. Document those relationships, but do not resolve tickets, change their status, make payments, update inventory, or otherwise modify the database.
Create or update `output/harness.md` with:

1. A section for every database table
2. A clear list or table of its fields
3. One short line explaining why that table matters to the agents
4. A concise summary of the relationships between tables
5. A section describing the three open tickets and the related records you found

Use only information supported by the actual database. Do not invent meanings or relationships when the schema or data does not establish them; label any reasonable interpretation as an inference.
Verify that:

* Every table is included
* Every table’s fields are documented accurately
* Each table has a short explanation of why it matters to the agents
* All three open tickets are covered
* Neither database file was changed
* `output/harness.md` was created successfully

Record this exact prompt under the Problem 2 section of `AI_prompts.md`. Stop after Problem 2 and do not begin Problem 3.
```

### Follow-up prompt

_[Only if one is actually used]_

### What was missing or incorrect

_[One sentence, only if a follow-up was needed]_

---

## Problem 3 — MCP Server with Three Ticket Tools

### Prompt

```text
Let’s work only on Problem 3.
Using the database analysis from Problem 2, build an MCP server inside `mcp_server/` using FastMCP. The server must use the working database at `campus_customs_new.db`, never the original `campus_customs.db`.
Before designing the tools, review the three open tickets- 101, 102, and 103 -and the related database records identified in Problem 2. Create exactly three MCP tools that the agents will need to make progress on those tickets.
For each tool:

* Give it a clear, specific name that describes the business lookup it performs.
* Tie it to an actual information need in ticket 101, 102, or 103.
* Query only the relevant database table or tables.
* Accept useful, well-defined input parameters rather than relying on hardcoded record IDs or values.
* Return structured results containing the database fields the agent needs to evaluate the ticket.
* Return a clear not-found or empty result when the requested record does not exist.
* Use parameterized SQL queries.
* Never invent, estimate, or silently substitute data.
* Do not modify the database; the three tools created in this problem should be read-only.

Avoid overly broad tools such as unrestricted SQL execution. Give agents only the narrow database access required for the tickets.
Create a short `mcp_server/README.md` explaining:

* What the MCP server is for
* That it uses `data/campus_customs_new.db`
* The names of its three tools
* What each tool reads and returns

Update `output/harness.md` by adding a Problem 3 section. For each of the three tools, document:

* Tool name
* Input parameters
* Output fields
* Database table or tables it reads
* Which ticket it helps unlock: 101, 102, or 103
* One specific sentence explaining why this tool is appropriate for that ticket

The final sentence must connect the tool’s returned information to the actual facts or decision required by the identified ticket. Do not use vague explanations such as “this tool reads inventory.” A stronger explanation would identify what the ticket needs to determine and explain how the tool’s database fields provide that evidence.
Make sure the tools and explanations are based on the actual database schema and ticket contents rather than assumed table structures.
You do not need to connect or run the MCP server in this problem. Perform safe static checks for syntax and imports if possible, but do not begin Problem 4.
Verify that:

* `mcp_server/` contains a FastMCP server
* The server points only to `data/campus_customs_new.db`
* Exactly three ticket-relevant tools are defined
* Each tool uses database-backed information only
* `mcp_server/README.md` documents the server and all three tools
* `output/harness.md` identifies the table, ticket, and ticket-specific justification for every tool
* Neither database file was modified during this problem

Record this exact prompt under the Problem 3 section of `AI_prompts.md`.
```

### Follow-up prompt

_[Only if one is actually used]_

### What was missing or incorrect

_[One sentence, only if a follow-up was needed]_

---

## Problem 4 — Connect the MCP Server to Claude Code

### Prompt

```text
Let’s work only on Problem 4.
Connect the FastMCP server created in Problem 3 to Claude Code using an appropriate project-level MCP configuration. Inspect the existing files in `mcp_server/` first so the configuration uses the server’s actual entry point and required Python environment. Keep the configuration portable by using project-relative paths where supported.
After connecting the server:

1. Confirm that Claude Code can discover all three MCP tools.
2. Invoke each tool through the MCP connection at least once.
3. Use a realistic test request and arguments tied to the ticket that the tool was designed to support.
4. Confirm that every returned value matches the corresponding record in `data/campus_customs_new.db`.
5. Do not test the tools only by importing and calling their Python functions directly—the evidence must come from actual MCP tool calls.
6. Do not modify either database during these tests.

Save the test evidence as valid JSON at:
`output/mcp_smoke.json`
The JSON should contain one entry for each of the three MCP tools. Every entry must include:

* `prompt`: the exact request given to Claude Code
* `tool_name`: the MCP tool that was invoked
* `arguments`: the arguments passed to the tool
* `ticket_id`: the ticket the test supports
* `tool_output`: the complete structured result returned by the MCP tool
* `database_verification`: a concise statement confirming which table and record were checked and that the output matches `data/campus_customs_new.db`
* `status`: `passed` or `failed`

Use JSON-native values rather than placing the tool output inside a formatted string. Do not invent or manually substitute output values. If a tool fails, preserve the actual error in the evidence, fix the MCP configuration or tool implementation as needed, and rerun the test.
Verify at the end that:

* The MCP server is connected to Claude Code
* All three tools are discoverable
* All three tools were invoked through MCP
* `output/mcp_smoke.json` contains exactly three test entries
* Each entry contains the prompt, tool name, arguments, ticket ID, tool output, database verification, and status
* Every successful output matches the working database
* Neither database file was modified

Record this exact prompt under the Problem 4 section of `AI_prompts.md`. Stop after completing Problem 4 and do not begin Problem 5.
```

### Follow-up prompt

_[Only if one is actually used]_

### What was missing or incorrect

_[One sentence, only if a follow-up was needed]_

---

## Problem 5 — PydanticAI Agent Team

### Prompt

```text
I ran problem 4 again, should work now. Let’s work only on Problem 5 now.
Inspect the existing project, the database analysis in `output/harness.md`, the three open tickets, and the MCP server created in Problems 3–4. Then build the Campus Customs agent team using PydanticAI.
Create five clearly separated agents:

1. Boss Agent
   * Reviews open tickets and identifies the work required.
   * Delegates tasks to the appropriate specialist agents.
   * Coordinates work that requires information from multiple agents.
   * Tracks whether delegated work succeeded, failed, or requires human approval.
   * Must not fabricate a resolution when a specialist lacks the necessary data or authority.
2. Inventory Agent
   * Handles inventory levels, products, pricing, vendors, and replenishment-related questions.
   * Uses database facts to determine availability, pricing, vendor lead times, and relevant purchasing constraints.
   * Must not invent stock, prices, quantities, vendors, or lead times.
3. Accounting Agent
   * Handles invoices, cash accounts, payments, and financial checks.
   * Must verify the relevant invoice and available cash before recommending or preparing a payment.
   * Must never allow a cash balance to become negative.
   * Any actual payment requires explicit human approval; without approval, it may only prepare or recommend the action.
4. Facilities Agent
   * Handles leases, locations, facilities obligations, and related operational issues.
   * Must use the lease and other relevant database records rather than relying on assumptions.
5. Customer Service Agent
   * Handles customer-facing ticket analysis and drafts proposed customer communications.
   * It may draft responses but must never send an email, contact a customer, promise an unsupported outcome, or claim an action was completed when it was not.

Place:

* One detailed prompt file per agent in `backend/prompts/`
* Shared Pydantic data models in `backend/models.py`
* The agent implementations and orchestration code under `backend/`

Use the existing project structure where appropriate. The five roles must remain easy to identify.
Use `PORTKEY_API_KEY` for model access and use only `gpt-6-luna` for every agent. Do not place an API key in the source code, prompts, logs, documentation, or output files.
Each agent prompt must clearly explain:

* The agent’s role and responsibilities
* What work is within and outside its scope
* Which other agents it may delegate to
* When it should return work to the Boss Agent
* Which shop rules apply to its work
* That database facts must come from MCP tools
* That it must not invent missing information
* When human approval is required
* What conditions require it to stop or report that it cannot proceed

Give the agents full delegation connectivity so they can transfer appropriate work to one another, while keeping the Boss Agent responsible for overall coordination. Use structured Pydantic models for delegation requests, agent results, approval status, errors, and other important data passed between agents. Prevent uncontrolled delegation loops by tracking delegation depth or steps and enforcing a clear maximum.
Expand the existing FastMCP server with any additional narrowly scoped tools the agents need to analyze and eventually work on tickets 101, 102, and 103.
For every new MCP tool:

* Base it on an actual requirement found in the open tickets.
* Use `data/campus_customs_new.db`, never the original database.
* Give it a specific business-purpose name.
* Use parameterized SQL.
* Accept clearly defined inputs.
* Return structured, database-backed results.
* Return explicit not-found or blocked results when appropriate.
* Give agents only the minimum database access required.
* Do not create unrestricted SQL or arbitrary database-update tools.
* Enforce business rules in deterministic code when possible rather than relying only on the model prompt.

All shop facts must reach the agents through the MCP server. Do not create a second database helper, direct-SQL agent tool, or separate shop-tools layer that bypasses MCP.
Incorporate the assignment’s operating rules:

* Use `desk.date_today` as the shop’s current date rather than the computer’s date.
* Use vendor lead times recorded in the database.
* Treat an open unpaid vendor invoice as a blocker when the shop rules say the vendor will not ship new products.
* Require explicit human approval before any payment is executed.
* Refuse a payment if the relevant cash account lacks sufficient funds.
* Never permit a negative cash balance.
* Do not invent revenue or cash inflows.
* Do not send customer emails or contact vendors; drafts and proposed actions must remain internal.
* Clearly distinguish between proposed, approved, executed, blocked, and failed actions.

Wire the agent loops to append structured audit entries to `output/audit_trail.json`. Do not erase previous entries when a new run begins.
Each audit entry should record enough information to reconstruct the operational sequence without exposing private chain-of-thought. Include, where applicable:

* Timestamp
* Run ID
* Step number
* Acting agent
* Ticket ID
* Task or action attempted
* Delegation source and destination
* MCP tool called
* Tool arguments, excluding secrets
* Concise tool-result summary
* Approval status
* Outcome or error
* Stop or continuation reason

Do not record API keys, credentials, hidden reasoning, or unnecessary sensitive data.
Update `output/harness.md` with a Problem 5 section that includes:

* All five agents
* Each agent’s responsibilities and boundaries
* How delegation works
* Each existing and newly added MCP tool
* The table or tables used by every tool
* Which agent or agents use each tool
* Which ticket need the tool supports
* A specific explanation of how its returned fields help with that ticket

Also add a concise safety section covering:

* Human approval for payments
* Insufficient-funds protection
* Prevention of negative balances
* No unauthorized customer or vendor contact
* Prevention of invented shop facts
* MCP-only database access
* Protection of API keys and sensitive data
* Maximum agent steps and delegation depth
* Tool-call and token-budget limits
* Clear stopping behavior for repeated failures, missing data, and approval blockers

Update `mcp_server/README.md` so its tool list and descriptions match the complete MCP server after this problem.
Do not resolve the open tickets or execute business actions in this problem unless the assignment explicitly requires a build-time test. Perform safe validation of imports, syntax, Pydantic models, agent construction, MCP tool registration, and delegation wiring. Any test must avoid payments, customer contact, vendor contact, and database modification.
Verify that:

* All five PydanticAI agents exist
* There is one detailed prompt file per agent
* Shared structured models are in `backend/models.py`
* Every agent uses only `gpt-6-luna` through Portkey
* No API key is hardcoded
* Agents can delegate through bounded, structured workflows
* All database facts come through MCP
* The MCP server contains the tools required for the three open tickets
* Audit entries append rather than overwrite
* `output/harness.md` documents the agents, tools, tables, ticket connections, and safety controls
* `mcp_server/README.md` matches the implemented tool set
* The original database remains untouched

Record this exact prompt under the Problem 5 section of `AI_prompts.md`. Stop after Problem 5 and do not begin Problem 6.
```

### Follow-up prompt

_[Only if one is actually used]_

### What was missing or incorrect

_[One sentence, only if a follow-up was needed]_

---

## Problem 6 — Expected-Plan Desk Page

### Prompt

```text
Let’s work only on Problem 6.
Before running the agent team, create a planning page at `output/desk_tickets.html` showing what I expect the agents to do for each of the three open tickets.
First inspect:

* Tickets 101, 102, and 103 in `data/campus_customs_new.db`
* The five agent roles and their actual prompt files
* The implemented delegation structure
* The complete current MCP tool list
* `output/harness.md` and `mcp_server/README.md`

Use this evidence to create specific plans based on the actual tickets, agents, and tools. Do not invent ticket facts, tools, or database values.
Build `output/desk_tickets.html` as a self-contained page that can be opened directly by double-clicking it, without requiring a server. Include all CSS and JavaScript inside the HTML file.
The page must have five functional tabs:

1. Ticket 101
2. Ticket 102
3. Ticket 103
4. Cash
5. Reflection

There must be one separate tab for each ticket—do not combine tickets 101, 102, and 103 into one general Tickets tab.
For each ticket tab, include an Expected section containing:

* A concise summary of the ticket based on the database
* Which specialist agent the Boss Agent should call first
* A specific explanation of why that agent should be called first for this ticket
* Every additional delegation I expect to occur, in anticipated order
* The purpose of each delegation
* The specific MCP tools I expect the agents to call
* What each tool is expected to establish for this ticket
* Any likely approval requirement, blocker, or stopping condition
* The expected outcome, clearly labeled as a prediction rather than an actual result

Do not write vague plans such as “the Boss calls everyone.” Use only the agents whose expertise is relevant to that ticket. Tie every expected delegation and MCP tool call to a concrete question or action required by the ticket.
Each ticket tab must also reserve a clearly labeled Actual section for a later problem. Leave that section empty or display a brief note such as “To be completed after the agents run.” Do not simulate or invent actual agent results.
For the Cash and Reflection tabs, leave them blank or display a short “Coming later” message. Do not calculate cash information or write the reflection yet.
Make the interface clear and readable:

* Display the five tabs prominently
* Clearly indicate the active tab
* Show only one tab’s content at a time
* Use headings, cards, spacing, and simple professional CSS
* Ensure all tab buttons work when the file is opened locally
* Keep the page easy to scan without adding unnecessary features

Do not run the agent team, resolve any ticket, execute payments, contact customers or vendors, or modify either database in this problem.
Open or render `output/desk_tickets.html` and verify that:

* It opens correctly without a server
* Ticket 101, Ticket 102, and Ticket 103 each have their own tab
* Cash and Reflection have separate placeholder tabs
* All five tab buttons work
* Each ticket tab contains only the Expected plan plus reserved space for Actual results
* Each plan names the first specialist, explains why, lists the expected delegation sequence, and identifies ticket-specific MCP tools
* The plans do not send every specialist to every ticket
* No unsupported facts or nonexistent tools appear
* The databases remain unchanged

Record this exact prompt under the Problem 6 section of `AI_prompts.md`. Stop after Problem 6 and do not begin Problem 7.
```

### Follow-up prompt

_[Only if one is actually used]_

### What was missing or incorrect

_[One sentence, only if a follow-up was needed]_

---

## Problem 7 — FastAPI Backend

### Prompt

````text
Let’s work only on Problem 7.
Create the FastAPI backend in `backend/main.py` for the React dashboard that will be built in the next problem. Reuse the agent team, Pydantic models, MCP tools, audit system, and business rules already implemented. Do not create a second database-access or business-logic layer that bypasses the existing MCP architecture.
The backend must run from the `backend/` directory with:

```
uvicorn main:app --reload --port 8000
```

It must be available at:
`http://localhost:8000`
Implement browser-callable JSON API routes for the following functions:

1. List tickets
   * Return tickets 101, 102, and 103.
   * Include the ticket ID, relevant ticket information, and whether each ticket is open or resolved.
   * Suggested route: `GET /api/tickets`
2. Run the agent team on one ticket
   * Accept a ticket ID.
   * Validate that the ticket exists.
   * Start the Boss Agent on that ticket and allow the existing bounded delegation workflow to run.
   * Return a structured run ID and current result or status.
   * Suggested route: `POST /api/tickets/{ticket_id}/run`
3. Return recent agent events
   * Return structured events from `output/audit_trail.json`.
   * Include enough information for the dashboard to show which agent acted, what it said or concluded, which MCP tool it used, the outcome, and whether approval is pending.
   * Support filtering by ticket ID or run ID where practical.
   * Suggested route: `GET /api/events`
4. Approve a prepared payment or purchase
   * Accept the identifier of a specific pending action prepared by the agents.
   * Require an explicit request from the human approval button.
   * Validate that the action exists, is still pending, has not already been executed, and matches the amount and records originally prepared.
   * Recheck the current cash balance immediately before execution.
   * Reject the action if cash is insufficient.
   * Never allow the balance to become negative.
   * Perform the authorized database changes atomically.
   * Return the updated action status and resulting balance.
   * Suggested route: `POST /api/approvals/{action_id}/approve`
5. Return the current checking balance
   * Return the current checking balance from `cash_accounts`.
   * Use the authoritative database-backed implementation rather than cached or invented values.
   * Suggested route: `GET /api/cash/checking`
6. Reset the working database
   * Restore `data/campus_customs_new.db` from the unchanged original `data/campus_customs.db`.
   * Never alter the original database.
   * Make the reset an explicit POST action rather than a GET request.
   * Safely close database connections before replacing the working copy.
   * Return confirmation that the reset completed.
   * Suggested route: `POST /api/reset`

You may also add a simple health route such as `GET /api/health`.
Use Pydantic request and response models for the route contracts. Return meaningful HTTP status codes and structured errors, including:

* `400` for invalid requests
* `404` for missing tickets or actions
* `409` for already-executed, stale, blocked, or insufficient-funds actions
* `500` only for unexpected server failures

Make these routes callable by the React frontend from the browser:

* Add FastAPI CORS middleware.
* Permit the local frontend origins actually used by the project, such as `http://localhost:5173` and `http://localhost:3000`.
* Keep the permitted origins explicit rather than using an unrestricted wildcard.
* Support the HTTP methods and headers required by the dashboard.
* Return JSON consistently.
* Ensure browser preflight `OPTIONS` requests succeed.
* Keep route paths stable and clearly documented so the frontend can call them in Problem 8.
* If practical, define the API base URL on the frontend side later through configuration rather than hardcoding it throughout the UI.

Preserve all existing safety rules:

* Use only `data/campus_customs_new.db` for working changes.
* Never modify `data/campus_customs.db`.
* Agents may prepare a payment or purchase but may not execute it.
* Only the human-approval route may execute a prepared financial action.
* Revalidate pending actions and cash at approval time.
* Refuse insufficient-funds transactions.
* Never create a negative balance.
* Do not invent shop facts or cash inflows.
* Do not contact customers or vendors.
* Prevent duplicate execution through idempotent approval handling.
* Append meaningful route and execution events to `output/audit_trail.json` without recording secrets or private chain-of-thought.

Do not build the React dashboard yet. However, verify now that a future frontend can call every route:

* Start the backend using the required command.
* Test each non-destructive route over HTTP rather than only calling Python functions.
* Test CORS or browser-style preflight behavior using an allowed frontend origin.
* Confirm the OpenAPI documentation loads.
* Confirm invalid ticket and approval IDs return structured errors.
* Test the approval route safely without executing an unintended real payment; use a blocked, invalid, or controlled test case where necessary.
* Confirm that the reset route points from the original database to the working copy, never in the opposite direction.
* Stop the test server after verification.

Update `output/harness.md` with a Problem 7 section listing each implemented route in one line, including:

* HTTP method
* URL
* What it does
* Request input, if any
* Main response
* Which future dashboard control or display will call it

Also document the permitted frontend origins and the human-approval boundary.
Verify that:

* `backend/main.py` contains a working FastAPI application
* The required Uvicorn command starts it on port 8000
* All six required backend capabilities have routes
* The routes return structured JSON
* The React dashboard will be able to call them from an allowed local origin
* CORS preflight works
* Only the approval route can execute prepared payments or purchases
* Insufficient funds and duplicate approvals are rejected
* The reset route restores only the working database
* `output/harness.md` accurately lists the actual implemented routes
* No frontend dashboard is built yet
* The original database remains unchanged

Record this exact prompt under the Problem 7 section of `AI_prompts.md`. Stop after Problem 7 and do not begin Problem 8.
````

### Follow-up prompt

_[Only if one is actually used]_

### What was missing or incorrect

_[One sentence, only if a follow-up was needed]_

---

## Problem 8 — React Agent Dashboard

### Prompt

````text
Let’s work only on Problem 8.
Build the frontend agent dashboard in `frontend/` using React, Vite, and TypeScript. Inspect the actual FastAPI routes and response models created in Problem 7 before implementing the frontend. Do not assume route names or response fields that differ from the backend.
The dashboard must communicate with the FastAPI backend at:
`http://localhost:8000`
Use a centralized, configurable API base URL, such as a Vite environment variable with `http://localhost:8000` as the local default. Do not scatter hardcoded URLs throughout the components.
The frontend must call the real backend routes. Do not use hardcoded ticket information, simulated agent events, fake balances, or placeholder approval results when the backend is available.
At minimum, the dashboard must:

1. Display all three tickets
   * Show tickets 101, 102, and 103 from the backend.
   * Display each ticket’s current open or resolved status.
   * Provide enough ticket information for the user to understand the issue.
   * Refresh ticket status from the backend rather than managing it only in local React state.
2. Allow the human to select one ticket
   * Make the selected ticket visually clear.
   * Display its details, current status, and available actions.
   * Prevent accidental simultaneous runs of the same ticket.
3. Start the agent team
   * Include a clear control to run the agent team on the selected ticket.
   * Call the corresponding Problem 7 backend route.
   * Show loading, running, completed, blocked, and error states.
   * Disable duplicate run actions while a ticket is already running.
4. Show agent activity
   * Display the Boss, Inventory, Accounting, Facilities, and Customer Service agents distinctly.
   * Show what each participating agent is saying or doing during the run.
   * Show delegations and MCP tool usage using the recent-events route.
   * Poll or refresh the backend event feed while a ticket is running.
   * Do not display hidden chain-of-thought; show only the structured operational events returned by the backend.
5. Show the completed run
   * Refresh the selected ticket from the backend when the run finishes.
   * Mark it resolved only when the backend reports it as resolved.
   * Show a concise summary of what each participating agent did.
   * Clearly display blocked, approval-pending, or unresolved outcomes rather than falsely showing success.
6. Handle human approvals
   * Display a clear approval card when an agent prepares a payment or purchase.
   * Show the action type, amount, purpose, related ticket, and current approval status.
   * Require a deliberate human click before calling the approval route.
   * Add a confirmation step before submitting the approval.
   * Disable the button after submission to prevent duplicate execution.
   * Clearly display approved, executed, blocked, stale, duplicate, and insufficient-funds responses.
   * The frontend must never change cash locally or claim that a payment succeeded before receiving backend confirmation.
7. Show the checking balance
   * Retrieve the current checking balance from the backend.
   * Format it consistently as currency.
   * Refresh it after an approved payment or purchase.
   * Ensure the displayed balance reflects the backend and decreases only after a successful approved transaction.

Also include a visible Reset working database control that calls the Problem 7 reset route. Require confirmation before resetting, clearly explain that it restores the working database to its original values, and refresh tickets, events, approvals, and cash after a successful reset.
Design the dashboard as a polished operations desk that a real person would enjoy using. Use a thoughtful Campus Customs/Yale-inspired visual identity, including deep Yale blue, warm neutral backgrounds, restrained accent colors, and clear status colors. Keep it professional rather than making it look like a generic developer console.
Suggested layout:

* Header with dashboard name, backend connection status, and current checking balance
* Ticket navigation showing tickets 101, 102, and 103
* Main selected-ticket workspace
* Agent activity area with distinct visual treatment for each agent
* Approval area that becomes prominent only when human action is needed
* Final run summary and ticket status
* Reset control placed separately from ordinary workflow controls

Make each agent visually recognizable through a consistent name, icon or initials, and accent color while maintaining accessible contrast. Use badges for statuses such as Open, Running, Approval Needed, Blocked, and Resolved.
Add proper frontend behavior:

* Typed TypeScript interfaces matching the actual backend schemas
* A centralized API client
* Loading indicators
* Empty states
* Clear, human-readable errors
* Retry or refresh controls where appropriate
* Responsive behavior for common laptop widths
* Keyboard-accessible tabs and buttons
* Visible focus states
* Semantic headings and labels
* No unnecessary external services or fabricated data

Ensure the frontend can actually call the backend:

* Run the backend at `http://localhost:8000`.
* Run the Vite frontend, normally at `http://localhost:5173`.
* Confirm the backend allows the frontend origin through CORS.
* Test the routes from the running React application, not only with command-line requests.
* Confirm browser requests do not fail because of CORS, incorrect paths, or mismatched schemas.

The frontend must start from the `frontend/` directory with:

```
npm run dev
```

Create `output/design.md` explaining:

* The dashboard layout
* The visual style and color choices
* How the five agents are visually distinguished
* How open, running, blocked, approval-pending, and resolved tickets appear
* How cash and approval requests are displayed
* How the dashboard communicates with the backend
* The creative choices that make the dashboard pleasant and practical for a human operator

Run and visually verify the completed dashboard. Test at least the following:

* All three tickets load from the backend
* Selecting each ticket works
* Starting an agent run calls the backend
* Agent events appear and refresh
* The summary displays after a run
* Ticket status refreshes from the backend
* Approval controls call the real approval route
* Duplicate approvals are prevented
* The checking balance refreshes after successful approval
* Backend errors appear clearly
* The reset control requires confirmation and refreshes the dashboard
* The page remains readable at a typical laptop viewport
* There are no browser console errors or failed CORS requests

Do not bypass the backend, directly access SQLite from the frontend, hardcode database values, or simulate successful financial actions.
Record this exact prompt under the Problem 8 section of `AI_prompts.md`. Stop after Problem 8 and do not begin Problem 9.
````

### Follow-up prompt

_[Only if one is actually used]_

### What was missing or incorrect

_[One sentence, only if a follow-up was needed]_

---

## Problem 9 — End-to-End Ticket Resolution Run

### Prompt

```text
Let’s work only on Problem 9.
Perform a clean, end-to-end run of the Campus Customs system and resolve tickets 101, 102, and 103 through the React dashboard and FastAPI backend.
Before running any ticket:

1. Inspect the current project and confirm the backend, frontend, five-agent team, MCP server, approval workflow, and audit logging are available.
2. Reset `data/campus_customs_new.db` from the unchanged original `data/campus_customs.db` using the implemented reset workflow.
3. Never modify `data/campus_customs.db`.
4. Verify that the working database now matches the original starting state.
5. Read and record the starting checking balance from the working database after the reset.
6. Start the FastAPI backend and React dashboard using their required commands.
7. Confirm the dashboard successfully loads tickets 101, 102, and 103 from the backend.

Run the three tickets one at a time through the real dashboard workflow, in this order:

1. Ticket 101
2. Ticket 102
3. Ticket 103

For each ticket:

* Select the ticket in the React dashboard.
* Start the real agent team through the backend route.
* Allow the Boss Agent to delegate to only the relevant specialists.
* Ensure all shop facts come from the MCP server.
* Observe and preserve the actual agent events, delegations, tool calls, results, blockers, and stop reasons.
* Do not replace a failed real run with invented results.
* If a run fails because of an implementation problem, diagnose and fix the smallest appropriate issue, then rerun the affected ticket.
* Do not bypass the agents, MCP tools, backend routes, or dashboard by manually editing the ticket outcome.

If an agent prepares a payment or purchase:

* Stop at the human-approval boundary.
* Show me the exact proposed action, including the ticket, purpose, payee or vendor, amount, current checking balance, and expected resulting balance.
* Do not click Approve or call the approval route on my behalf.
* Wait for my explicit approval before proceeding.
* After I approve, execute the action only through the dashboard’s human-approval control and backend approval route.
* Revalidate the action and available cash immediately before execution.
* Refuse insufficient-funds, stale, duplicate, or already-executed requests.
* Never allow the checking balance to become negative.

Do not contact customers or vendors. Customer communications and vendor communications must remain drafts or internal proposed actions.
After each ticket completes:

* Confirm its final status from the backend and working database.
* Confirm whether it is resolved, blocked, or still open.
* Record a short outcome supported by the real run.
* Record every agent that actually participated and its contribution.
* Record the actual delegation sequence.
* Record the MCP tools actually used.
* Record any human approval and resulting financial action.
* Record the checking balance after the ticket.
* Capture a real screenshot of the React dashboard showing the completed state for that ticket.

Update `output/desk_tickets.html` from Problem 6:

* Preserve each ticket’s original Expected section exactly so it can be compared with the run.
* Fill the reserved Actual section for tickets 101, 102, and 103 using evidence from the real audit trail and database.
* For each Actual section, include:
   * Final ticket status
   * Actual outcome
   * Agents that worked
   * Actual delegation order
   * MCP tools used
   * Important tool findings
   * Human approvals requested and received
   * Any financial effect
   * Any errors, retries, blockers, or deviations from the Expected plan
* Do not rewrite the Expected plan after seeing the Actual result.

Fill the Cash tab in `output/desk_tickets.html` with an itemized reconciliation containing:

* Starting checking balance immediately after the reset
* Ticket 101 cash change and why
* Ticket 102 cash change and why
* Ticket 103 cash change and why
* The specific payment or purchase associated with every nonzero change
* The exact dollar amount of every change
* A `$0.00` line and explanation for any ticket that caused no cash movement
* Total cash outflow
* Ending checking balance

Use exact currency arithmetic to the cent. Verify:
`starting checking balance − approved cash outflows = ending checking balance`
The ending balance displayed in the Cash tab must exactly match the current checking balance in `cash_accounts` in `data/campus_customs_new.db`.
Create `output/resolved_tickets.json` as valid structured JSON with one object for each of tickets 101, 102, and 103. Each object must include:

* `id`
* `final_status`
* `short_outcome`
* `agents_involved`
* `agent_contributions`
* `delegations`
* `mcp_tools_used`
* `human_approvals`
* `cash_change`
* `final_checking_balance_after_ticket`
* `run_id`

Populate this file from the actual runs, not from the Expected plans.
Create `output/resolved_board.html`, a page that can be opened by double-clicking it. It must display a real screenshot of the React dashboard for each resolved ticket:

* Ticket 101 screenshot
* Ticket 102 screenshot
* Ticket 103 screenshot

Save the screenshot image files inside `output/` using clear filenames and reference them with working relative paths, or embed them directly in the HTML. Add headings and brief captions identifying the ticket and final status. Verify that all three screenshots appear when `resolved_board.html` is opened locally.
Append all real agent-run events to `output/audit_trail.json`. Do not erase earlier entries. Ensure the real runs have distinct run IDs so they can be separated from earlier tests. Record structured operational events without API keys, credentials, or private chain-of-thought.
Finish `output/harness.md` so it accurately covers:

* All database tables and why they matter
* All MCP tools and the tables they use
* Which agents use each tool
* The five agents and their scopes
* Delegation behavior
* FastAPI routes
* React dashboard behavior
* Human-approval workflow
* Audit logging
* Database reset behavior
* Safety rules
* Insufficient-funds and negative-balance protections
* Token, tool-call, and agent-step limits

After all three tickets have completed, verify that:

* The working database was reset before the full run
* The starting checking balance was recorded after the reset
* Tickets 101, 102, and 103 were run through the dashboard
* All three have accurate final statuses
* No payment or purchase occurred without my explicit approval
* Every approved financial action appears in the database and audit trail
* The ending checking balance matches `cash_accounts`
* The cash reconciliation is mathematically correct
* The Expected sections remain unchanged
* Every Actual section reflects the real run
* `output/resolved_tickets.json` is valid and matches the real results
* `output/resolved_board.html` opens locally and shows all three real screenshots
* `output/audit_trail.json` contains the real runs
* `output/harness.md` completely and accurately documents the implemented system
* The original database remains unchanged
* No API key or credential appears in any output

Record this exact prompt under the Problem 9 section of `AI_prompts.md`. Stop after Problem 9 and do not begin Problem 10.
```

### Follow-up prompt

```text
can we reverse my previous approvals?
```

```text
please reset the working database and restart Problem 9
```

### What was missing or incorrect

After the first attempt's approvals had been executed, the system had no way to reverse them, so the working database was reset and Problem 9 was restarted as a clean run.

---

## Problem 10 — Reflection

### Prompt

```text
No need to restart backend. Let’s work only on Problem 10. 

Inspect the completed HW5 project and the evidence displayed in `output/desk_tickets.html`, including the ticket tabs, Cash tab, audit trail, expected plans, actual results, approval history, and supporting database-backed facts.

Update only the Reflection tab in `output/desk_tickets.html`. Use the completed reflection below as my personal reflection. Insert it faithfully and do not replace it with an AI-written reflection, change its conclusions, or invent additional events. You may make minor formatting changes for readability, such as headings, paragraphs, and bullet points.

My Reflection

1. Evaluation of the agents’ performance

* Ticket 101: Out-of-stock white T-shirt: The agents performed well at diagnosing the immediate causes of this ticket, but they could not fully resolve the customer’s inventory problem with the available data and tools. The Inventory Agent correctly used database-backed information to confirm that the requested `CC-TEE-WHITE` shirt in size S was out of stock. It did not invent a quantity, claim that another size was equivalent, or falsely tell the customer that the item was available. The agents also found that an unpaid Bulldog Print Co invoice, invoice 501 for $840, was an operational blocker. The Accounting Agent verified the invoice and checked the available cash before presenting the payment for approval. The shop began with $3,400 in checking, so the approved $840 payment reduced the balance to $2,560 without creating a negative balance. However, paying the invoice did not automatically solve the shortage. The proposed purchase of one size-S shirt could not be safely completed because the available records did not establish a sufficiently reliable SKU-to-vendor relationship or provide all the purchasing information needed for a valid order. The agents correctly left that proposed action pending instead of inventing a vendor, purchase price, or purchase order. This was a good example of safe agent behavior. The team made measurable progress by identifying and removing a vendor-payment blocker, but it did not falsely claim that the customer’s shirt had been replenished. The remaining limitation came from missing operational data and authority, not from a failure to investigate.


* Ticket 102: Overdue rent: Ticket 102 was the strongest and most complete agent result. The Facilities Agent found the relevant lease for the Chapel Street location and verified that $2,400 was due to Elm City Properties on September 2, 2026. The Accounting Agent then checked the available cash and confirmed that the rent could be paid. After the earlier $840 vendor payment, the checking balance was $2,560. The $2,400 rent payment therefore left $160, which remained nonnegative. The agents presented the payment for human approval rather than executing it automatically. After approval, the payment was recorded and the lease’s next due date advanced to October 2, 2026. The ticket was then presented for resolution approval and marked resolved. The agents followed the approval boundary, used the database instead of assumptions, and left a clear record of the financial effect. This ticket demonstrates that the multi-agent workflow works particularly well when the database contains a complete obligation, a known amount, a valid payee, and sufficient cash. 
* Ticket 103: Bulk hoodie discount: The agents also handled Ticket 103 responsibly. The Yale AI Club requested 20 `CC-HOOD-NAVY` hoodies in size M and asked for a bulk discount. The Inventory Agent verified that only eight units were on hand, creating a shortage of 12. It also found the database-backed list price of $58 per hoodie and unit cost of $22. At the list price, the gross margin would be $36 per unit, or approximately 62.1%. The team did not invent a bulk-discount policy. The available records did not establish an approved discount amount or rule, so the agents correctly treated the pricing decision as requiring human approval. The Customer Service Agent prepared an internal draft but did not send it, promise that all 20 hoodies were available, or offer an unsupported discount. This was a strong result because the agents separated verified facts from decisions requiring managerial judgment. They established the stock shortage and relevant pricing information but stopped before making a commercial commitment that the tools and database did not authorize. The ticket remained in an approval-needed state rather than being falsely described as fully resolved.


2. Comparison of actual results with the expected plans

* Ticket 101: The expected plan was to verify the requested product and size, inspect inventory, determine whether replenishment was possible, identify any vendor-related blockers, and avoid promising stock until the facts were confirmed. The actual workflow followed most of that plan. It confirmed that size S was out of stock and found the overdue $840 Bulldog Print Co invoice. It also verified that the business had enough cash and, after human approval, paid that invoice. The actual result differed from a complete ideal resolution because the team could not confidently place the replenishment order. The database did not provide enough verified information to connect the exact SKU and size to an appropriate vendor purchase with a supported unit cost and order record. The agents therefore stopped instead of creating unsupported purchasing information. That deviation was appropriate because the expected plan depended on data that was not actually available.


* Ticket 102: The expected plan was to locate the relevant lease, verify the payee, amount, and due date, check the available cash, request human approval, execute the payment only after approval, update the next due date, and resolve the ticket. The actual workflow closely matched this plan. The agents found lease 1 for the Chapel Street location, verified the $2,400 obligation to Elm City Properties, and confirmed sufficient funds. They requested approval, recorded the approved payment, reduced checking from $2,560 to $160, updated the next due date to October 2, 2026, and then resolved the ticket with human approval. This ticket had the smallest gap between the expected and actual paths because the database and existing tools supplied all the information necessary for a controlled resolution.


* Ticket 103: The expected plan was to verify the requested hoodie, size, quantity, available stock, price, and cost; determine whether an established discount policy existed; identify the shortage; and prepare a response without sending it or making unsupported promises. The actual result closely followed that plan. The agents verified that the customer requested 20 medium navy hoodies, found only eight in stock, and calculated a shortage of 12. They retrieved the $58 list price and $22 unit cost and reported the resulting margin information. They also determined that no approved bulk-discount rule was available. Because the discount decision required human judgment, the agents stopped at an approval-needed state. The Customer Service Agent drafted a possible response but did not contact the customer. This difference between analysis and final resolution was intentional and consistent with the expected safety controls.


3. Work that would have been simpler with one agent

* Ticket 102 would have been the clearest candidate for a single agent with tools. Its workflow was mostly linear: locate the lease, verify the amount and due date, check the cash balance, request approval, execute the approved payment, and update the lease. Separate Facilities and Accounting Agents made the responsibilities clear, but the handoffs added coordination overhead to a relatively straightforward task.


* Ticket 101 benefited more from specialized agents because it crossed inventory, vendor, accounting, and customer-service concerns. Ticket 103 also benefited from separating inventory research from customer communication. A single agent could have performed the lookups and drafted the response, but the specialist structure made it clearer which facts came from inventory records and which customer-facing statements still required approval.


* The main benefit of the multi-agent design was separation of responsibility. The main cost was additional delegation and audit activity, even when one tool-enabled agent could have performed the work sequentially. For simple, low-risk research tasks, one agent may be more efficient. For tasks involving payments, stock commitments, or customer promises, the specialist boundaries are more valuable.


4. Three additional problems the current team could solve

A. Checking product availability for a customer

The current team could answer a customer who asks whether a particular product, color, and size is available. The Inventory Agent could retrieve the exact stock quantity from the database, while the Customer Service Agent could prepare a response based on that result. If the requested variation were unavailable, the response could state that clearly without inventing stock or promising a restock date.

B. Reviewing an upcoming facility payment

The current team could identify an approaching rent or lease obligation, verify its amount and due date, compare it with the available cash balance, and prepare it for human approval. The Facilities Agent and Accounting Agent already demonstrated this workflow on Ticket 102. The payment would still require explicit approval, and the insufficient-funds protection would prevent an unsafe transaction.

C. Investigating a vendor invoice that blocks replenishment

The current team could investigate whether an unpaid vendor invoice is preventing the shop from receiving more merchandise. The Inventory Agent could identify the replenishment need and vendor relationship, while the Accounting Agent could inspect the open invoice and cash balance. The Boss Agent could then present the blocker and a proposed payment for approval. This is similar to the successful portion of Ticket 101.

5. Three problems the current team could not fully solve

A. Creating and approving a bulk-discount policy

The current team could calculate stock, list price, unit cost, and gross margin, but it could not independently decide what bulk discount should be authorized. Resolving that problem would require a Pricing Agent or an expanded managerial-pricing function. It would also need tools or tables containing approved discount tiers, minimum acceptable margins, customer categories, past order history, and the person authorized to approve exceptions.

This limitation appeared directly in Ticket 103. The agents could provide decision support, but they could not transform the absence of a policy into an approved discount.

B. Forecasting demand and selecting optimal reorder quantities

The current team could report current inventory and known shortages, but it could not reliably forecast future demand or decide how many units should be purchased. A Planning or Forecasting Agent would need access to historical sales by SKU, seasonality, upcoming campus events, current reservations, supplier lead times, minimum order quantities, and inventory carrying costs.

Without those data and tools, any reorder recommendation would be based on guesswork. Ticket 101 showed why knowing that one unit is currently needed is not the same as knowing the economically appropriate reorder quantity.

C. Completing external purchasing or communication

The current team could prepare internal recommendations and customer-response drafts, but it could not place a real vendor order, send an email, or confirm delivery with an external party. Completing those actions would require narrowly scoped Procurement and Communications tools connected to approved external systems.

Those tools should still require human approval and should record exactly what was sent or ordered. A Procurement Agent would need authenticated vendor-ordering capabilities, while a Communications Agent would need a controlled email tool. The present system appropriately stops before these external actions.

Overall assessment

The strongest feature of the system was its refusal to substitute model confidence for database evidence. Across the three tickets, the agents used tools to verify stock, prices, costs, invoices, leases, and cash balances. They also respected human-approval boundaries for payments, ticket resolution, discounts, and customer communications.

The system was most successful on Ticket 102 because the database contained a complete and actionable path. Ticket 101 demonstrated both useful progress and the importance of stopping when purchasing data was incomplete. Ticket 103 demonstrated that accurate operational analysis does not automatically authorize a pricing decision.

The multi-agent design added complexity, but it made responsibilities and approval boundaries visible. The audit trail and ticket-specific evidence also made it possible to compare what was expected with what actually happened. The most important future improvements would be better purchasing data, an approved discount-policy structure, demand-planning tools, and controlled external-action tools.

Implementation instructions

- Place the complete reflection above in the Reflection tab of `output/desk_tickets.html`.
- Keep all existing ticket, Cash, Expected, Actual, approval, and evidence content intact.
- Use readable headings, paragraphs, and lists consistent with the existing dashboard.
- Do not change database records, ticket outcomes, financial amounts, or audit entries.
- Do not perform new agent runs or business actions.
- Open or render the updated HTML and visually verify that the entire Reflection tab is readable.
- Verify that the reflection accurately matches the ticket evidence and that all five required questions are answered.
- Record this exact prompt under the Problem 10 section of `AI_prompts.md`.
- Stop after Problem 10 and do not begin another problem.
```

### Follow-up prompt

```text
why are not all tickets resolved?
```

```text
Preserve the actual final ticket outcomes from Problem 9:

* Ticket 102 is resolved.
* Ticket 101 remains open because the requested size is still out of stock, the proposed restock purchase was not approved, the system cannot place an external vendor order or verify receipt of new inventory, and the customer response remains an unsent draft.
* Ticket 103 remains open because the database contains no approved bulk-discount policy, only 8 of the requested 20 hoodies are in stock, the system cannot determine or apply an authorized discount, no replenishment plan exists for the remaining 12 units, and the customer response remains an unsent draft.

Do not alter these statuses merely to make all three tickets appear resolved. The open tickets are accurate outcomes demonstrating that the agents stopped when required data, authority, or external capabilities were missing.
In the reflection, explain that success does not always mean closing a ticket. For Tickets 101 and 103, the agents succeeded at investigation, fact verification, and safe escalation, but the underlying business issues remain unresolved. Clearly distinguish agent-performance success from ticket-resolution status.
Do not add new stock-receipt, vendor-ordering, discount-approval, pricing-policy, or email-sending capabilities during Problem 10. Do not rerun the tickets or change the Problem 9 evidence.
```

### What was missing or incorrect

The first reflection did not explicitly distinguish the agents' performance from the tickets' resolution status, so it did not explain why Tickets 101 and 103 correctly remained open.
