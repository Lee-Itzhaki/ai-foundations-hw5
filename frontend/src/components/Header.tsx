import type { CashBalance, HealthResponse } from '../api/types'
import { API_BASE_URL } from '../api/client'
import { money } from '../format'

interface Props {
  health: HealthResponse | null
  healthError: string | null
  cash: CashBalance | null
  cashError: string | null
  cashFlash: boolean
  shopDate: string | null
  pendingCount: number
  onRefresh: () => void
  refreshing: boolean
}

export function Header({ health, healthError, cash, cashError, cashFlash, shopDate, pendingCount, onRefresh, refreshing }: Props) {
  const conn = healthError ? 'offline' : !health ? 'checking' : health.status === 'ok' ? 'online' : 'degraded'
  const connLabel = { offline: 'Backend offline', checking: 'Connecting…', online: 'Backend connected', degraded: 'Backend degraded' }[conn]
  return (
    <header className="masthead">
      <div className="brand">
        <span className="crest" aria-hidden="true">CC</span>
        <div>
          <h1>Campus Customs <span className="brand-sub">Operations Desk</span></h1>
          <p className="brand-meta">
            {shopDate ? <>Shop date <strong>{shopDate}</strong></> : 'Shop date unavailable'}
            <span className="dot-sep" aria-hidden="true">·</span>
            <span title={API_BASE_URL}>Agents on {health?.model ?? 'gpt-6-luna'}</span>
          </p>
        </div>
      </div>

      <div className="masthead-right">
        <div className={`conn conn-${conn}`} role="status" aria-live="polite" title={healthError ?? API_BASE_URL}>
          <span className="conn-dot" aria-hidden="true" />
          {connLabel}
          {health && !health.model_configured && <span className="conn-note">· model key missing</span>}
        </div>

        {pendingCount > 0 && (
          <div className="pending-chip" role="status">{pendingCount} awaiting approval</div>
        )}

        <div className={`cash ${cashFlash ? 'cash-flash' : ''}`} aria-live="polite">
          <span className="cash-label">Checking</span>
          <span className="cash-amount">{cash ? money(cash.balance) : cashError ? 'Unavailable' : '…'}</span>
          {cash && <span className="cash-asof">as of {cash.as_of}</span>}
        </div>

        <button type="button" className="btn btn-ghost-light" onClick={onRefresh} disabled={refreshing}>
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
    </header>
  )
}
