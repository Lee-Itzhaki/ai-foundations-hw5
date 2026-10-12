// The single place that talks to the FastAPI backend.
import type {
  ActionList, ApproveResponse, CashBalance, ErrorBody, EventList, HealthResponse,
  ResetResponse, RunStatus, TicketList,
} from './types'

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || 'http://localhost:8000'

/** A failed request, carrying the backend's structured error when there is one. */
export class ApiError extends Error {
  status: number
  code: string
  details?: unknown

  constructor(status: number, body: ErrorBody) {
    super(body.message)
    this.status = status
    this.code = body.code
    this.details = body.details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}) },
    })
  } catch {
    throw new ApiError(0, {
      code: 'network_error',
      message: `Can't reach the backend at ${API_BASE_URL}. Is it running?`,
    })
  }
  const text = await res.text()
  let data: unknown = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    throw new ApiError(res.status, { code: 'invalid_response', message: `Unexpected non-JSON response (HTTP ${res.status}).` })
  }
  if (!res.ok) {
    const err = (data as { error?: ErrorBody } | null)?.error
    throw new ApiError(res.status, err ?? { code: `http_${res.status}`, message: `Request failed (HTTP ${res.status}).` })
  }
  return data as T
}

function query(params: Record<string, string | number | undefined | null>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') q.set(k, String(v))
  const s = q.toString()
  return s ? `?${s}` : ''
}

export const api = {
  health: () => request<HealthResponse>('/api/health'),
  tickets: () => request<TicketList>('/api/tickets'),
  runTicket: (ticketId: number) => request<RunStatus>(`/api/tickets/${ticketId}/run`, { method: 'POST' }),
  run: (runId: string) => request<RunStatus>(`/api/runs/${encodeURIComponent(runId)}`),
  events: (p: { ticket_id?: number; run_id?: string; limit?: number }) =>
    request<EventList>(`/api/events${query(p)}`),
  approvals: (p: { status?: string; ticket_id?: number } = {}) =>
    request<ActionList>(`/api/approvals${query(p)}`),
  approve: (actionId: string, approvedBy: string) =>
    request<ApproveResponse>(`/api/approvals/${encodeURIComponent(actionId)}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: approvedBy, confirm: true }),
    }),
  checking: () => request<CashBalance>('/api/cash/checking'),
  reset: () => request<ResetResponse>('/api/reset', { method: 'POST', body: JSON.stringify({ confirm: true }) }),
}

/** Human-readable explanation of an error, preferring the backend's message. */
export function describeError(e: unknown): string {
  if (e instanceof ApiError) return e.message
  if (e instanceof Error) return e.message
  return 'Something went wrong.'
}
