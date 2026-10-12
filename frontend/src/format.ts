import type { AgentEvent, PreparedAction, ResultStatus, RunStatus, Ticket } from './api/types'

const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
export const money = (n: number | null | undefined) => (n === null || n === undefined ? '—' : usd.format(n))

export function time(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export const TICKET_TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price override',
}
export const ticketTypeLabel = (t: string) => TICKET_TYPE_LABEL[t] ?? t.replace(/_/g, ' ')

/** Strip the JSON quoting the audit summarizer adds around plain strings. */
export function cleanSummary(s: string | null | undefined): string {
  if (!s) return ''
  if (!s.startsWith('"')) return s
  try {
    return JSON.parse(s) as string
  } catch {
    // Truncated by the audit summarizer ("...text..."), so not valid JSON: strip quoting by hand.
    return s.slice(1).replace(/"$/, '').replace(/\\"/g, '"').replace(/\\n/g, ' ')
  }
}

export type DeskStatus = 'open' | 'running' | 'approval' | 'blocked' | 'failed' | 'resolved'

export const DESK_STATUS_LABEL: Record<DeskStatus, string> = {
  open: 'Open',
  running: 'Running',
  approval: 'Approval needed',
  blocked: 'Blocked',
  failed: 'Run failed',
  resolved: 'Resolved',
}

export interface Outcome { status: ResultStatus; at: string | null }

/** The latest Boss outcome for a ticket, read from the backend's audit events. */
export function latestOutcome(events: AgentEvent[], ticketId: number): Outcome | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i]
    if (e.event === 'database_reset') return null
    if (e.ticket_id === ticketId && e.event === 'agent_finished' && e.agent === 'boss')
      return { status: e.outcome as ResultStatus, at: e.timestamp }
  }
  return null
}

/** Status shown on the desk. "Resolved" comes only from the backend's ticket status. */
export function deskStatus(
  ticket: Ticket, run: RunStatus | undefined, actions: PreparedAction[], outcome: Outcome | null,
): DeskStatus {
  if (!ticket.is_open) return 'resolved'
  if (run?.status === 'running') return 'running'
  if (actions.some(a => a.status === 'pending_human_approval')) return 'approval'
  // A human decision made after the last run supersedes that run's "needs approval" outcome.
  const decidedSince = outcome?.at
    ? actions.some(a => ['executed', 'approved'].includes(a.status) && a.updated_at > outcome.at!)
    : false
  if (decidedSince) return 'open'
  const s = run?.report?.tickets.find(t => t.ticket_id === ticket.id)?.status ?? outcome?.status
  if (run?.status === 'failed' && !run.report) return 'failed'
  if (s === 'blocked') return 'blocked'
  if (s === 'failed') return 'failed'
  if (s === 'needs_human_approval' || s === 'partial') return 'approval'
  return 'open'
}

export const RESULT_LABEL: Record<ResultStatus, string> = {
  succeeded: 'Succeeded',
  partial: 'Partial',
  needs_human_approval: 'Needs human approval',
  blocked: 'Blocked',
  failed: 'Failed',
}
