import type { HealthResponse, RunStatus, Ticket } from '../api/types'
import type { DeskStatus } from '../format'
import { dateTime, ticketTypeLabel, time } from '../format'
import { StatusBadge } from './StatusBadge'

export interface RunUiState {
  phase: 'idle' | 'starting' | 'running' | 'completed' | 'failed'
  run?: RunStatus
  error?: string
  errorCode?: string
}

interface Props {
  ticket: Ticket
  status: DeskStatus
  runState: RunUiState
  health: HealthResponse | null
  backendDown: boolean
  onRun: () => void
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="field">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

export function TicketWorkspace({ ticket, status, runState, health, backendDown, onRun }: Props) {
  const busy = runState.phase === 'starting' || runState.phase === 'running'
  const noModel = health ? !health.model_configured : false
  const disabledReason = !ticket.is_open ? 'This ticket is resolved.'
    : busy ? 'The agent team is already working on this ticket.'
    : backendDown ? 'The backend is not reachable.'
    : noModel ? 'The backend has no PORTKEY_API_KEY, so agents cannot run.'
    : null

  return (
    <section className="card ticket-card" aria-labelledby="ticket-heading">
      <div className="ticket-head">
        <div>
          <p className="eyebrow">{ticketTypeLabel(ticket.type)} · Ticket #{ticket.id}</p>
          <h2 id="ticket-heading">{ticket.subject}</h2>
          <p className="muted">From <strong>{ticket.requester}</strong> · received {dateTime(ticket.created_at)}</p>
        </div>
        <StatusBadge status={status} />
      </div>

      {ticket.notes && <blockquote className="ticket-notes">“{ticket.notes}”</blockquote>}

      <dl className="fields">
        {ticket.sku && <Field label="Item"><code>{ticket.sku}</code></Field>}
        {ticket.size && <Field label="Size">{ticket.size}</Field>}
        {ticket.qty !== null && <Field label="Quantity">{ticket.qty}</Field>}
        {ticket.invoice_id !== null && <Field label="Linked invoice">#{ticket.invoice_id}</Field>}
        {ticket.lease_id !== null && <Field label="Linked lease">#{ticket.lease_id}</Field>}
        <Field label="Database status"><code>{ticket.status}</code></Field>
      </dl>

      <div className="run-bar">
        <div className="run-bar-text">
          {runState.phase === 'idle' && <span className="muted">The Boss Agent will read this ticket and delegate to the specialists it needs.</span>}
          {runState.phase === 'starting' && <span><span className="spinner" aria-hidden="true" /> Starting the agent team…</span>}
          {runState.phase === 'running' && (
            <span><span className="spinner" aria-hidden="true" /> Agents are working · run <code>{runState.run?.run_id}</code> started {time(runState.run?.started_at)}</span>
          )}
          {runState.phase === 'completed' && (
            <span className="ok-text">Run <code>{runState.run?.run_id}</code> finished at {time(runState.run?.finished_at)}. See the summary below.</span>
          )}
          {runState.phase === 'failed' && (
            <span className="err-text" role="alert">
              {runState.errorCode ? <><strong>Couldn't run:</strong> </> : <strong>Run failed: </strong>}
              {runState.error ?? runState.run?.error ?? 'Unknown error.'}
            </span>
          )}
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onRun}
          disabled={disabledReason !== null}
          aria-describedby={disabledReason ? 'run-disabled-reason' : undefined}
        >
          {busy ? 'Running…' : runState.phase === 'completed' || runState.phase === 'failed' ? 'Run agents again' : 'Run agent team'}
        </button>
      </div>
      {disabledReason && !busy && <p id="run-disabled-reason" className="muted small run-reason">{disabledReason}</p>}
    </section>
  )
}
