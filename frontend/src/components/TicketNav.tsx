import { useRef } from 'react'
import type { Ticket } from '../api/types'
import type { DeskStatus } from '../format'
import { ticketTypeLabel } from '../format'
import { StatusBadge } from './StatusBadge'

interface Props {
  tickets: Ticket[]
  statuses: Record<number, DeskStatus>
  selectedId: number | null
  onSelect: (id: number) => void
  loading: boolean
  error: string | null
  onRetry: () => void
}

export function TicketNav({ tickets, statuses, selectedId, onSelect, loading, error, onRetry }: Props) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  function onKey(e: React.KeyboardEvent, i: number) {
    const next = e.key === 'ArrowDown' || e.key === 'ArrowRight' ? i + 1
      : e.key === 'ArrowUp' || e.key === 'ArrowLeft' ? i - 1
      : e.key === 'Home' ? 0 : e.key === 'End' ? tickets.length - 1 : null
    if (next === null) return
    e.preventDefault()
    const j = (next + tickets.length) % tickets.length
    onSelect(tickets[j].id)
    refs.current[j]?.focus()
  }

  return (
    <nav className="ticket-nav" aria-label="Tickets">
      <h2 className="section-label">Desk tickets</h2>
      {loading && tickets.length === 0 && <p className="muted small">Loading tickets…</p>}
      {error && (
        <div className="inline-error" role="alert">
          <p>{error}</p>
          <button type="button" className="btn btn-small" onClick={onRetry}>Retry</button>
        </div>
      )}
      {!loading && !error && tickets.length === 0 && <p className="muted small">No tickets in the database.</p>}
      <div role="tablist" aria-orientation="vertical" aria-label="Select a ticket" className="ticket-tabs">
        {tickets.map((t, i) => {
          const selected = t.id === selectedId
          return (
            <button
              key={t.id}
              ref={el => { refs.current[i] = el }}
              role="tab"
              id={`ticket-tab-${t.id}`}
              aria-selected={selected}
              aria-controls="ticket-panel"
              tabIndex={selected || (selectedId === null && i === 0) ? 0 : -1}
              className={`ticket-tab ${selected ? 'is-selected' : ''}`}
              onClick={() => onSelect(t.id)}
              onKeyDown={e => onKey(e, i)}
            >
              <span className="ticket-tab-top">
                <span className="ticket-num">#{t.id}</span>
                <StatusBadge status={statuses[t.id] ?? 'open'} />
              </span>
              <span className="ticket-tab-subject">{t.subject}</span>
              <span className="ticket-tab-meta">{ticketTypeLabel(t.type)} · {t.requester}</span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
