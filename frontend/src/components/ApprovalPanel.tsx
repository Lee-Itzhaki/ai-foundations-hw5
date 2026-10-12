import { useRef, useState } from 'react'
import type { PreparedAction } from '../api/types'
import { ApiError, api } from '../api/client'
import { AGENTS } from '../agentMeta'
import { AgentAvatar } from '../agents'
import { dateTime, money } from '../format'
import { Pill } from './StatusBadge'

interface Props {
  actions: PreparedAction[] // actions for the selected ticket
  loading: boolean
  error: string | null
  onRetry: () => void
  onDecided: () => Promise<void> // refresh approvals, cash, events, tickets
  lastResetAt: string | null // timestamp of the latest working-database reset, from the audit trail
}

type Result = { tone: 'success' | 'info' | 'blocked' | 'muted'; title: string; message: string }

const CODE_TITLES: Record<string, string> = {
  insufficient_funds: 'Insufficient funds: not paid',
  action_stale: 'Stale: amounts changed since the agents prepared this',
  action_blocked: 'Blocked by a shop rule',
  action_executed: 'Duplicate: this payment was already executed',
  action_approved: 'Duplicate: this purchase was already approved',
  action_not_pending: 'Duplicate: this action is no longer pending',
  action_not_found: 'Action not found',
}

function kindLabel(a: PreparedAction) {
  if (a.kind === 'purchase') return 'Purchase'
  if (a.kind === 'ticket_resolution') return 'Ticket resolution'
  return a.payment_kind === 'lease_rent' ? 'Rent payment' : a.payment_kind === 'vendor_invoice' ? 'Vendor invoice payment' : 'Payment'
}

function ApprovalCard({ action, onDecided, result, setResult, undoneByReset }: {
  action: PreparedAction
  undoneByReset: boolean
  onDecided: () => Promise<void>
  result: Result | undefined
  setResult: (r: Result) => void
}) {
  const [step, setStep] = useState<'idle' | 'confirm' | 'submitting' | 'done'>('idle')
  const [approver, setApprover] = useState(() => localStorage.getItem('cc-approver') ?? '')
  const inFlight = useRef(false) // synchronous guard: a fast double-click can't submit twice
  const pending = action.status === 'pending_human_approval'
  const prep = AGENTS[action.prepared_by as keyof typeof AGENTS]

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!approver.trim() || inFlight.current) return
    inFlight.current = true
    setStep('submitting')
    localStorage.setItem('cc-approver', approver.trim())
    try {
      const r = await api.approve(action.action_id, approver.trim())
      setResult(r.executed
        ? { tone: 'success', title: action.kind === 'ticket_resolution' ? 'Resolved' : 'Executed', message: `${r.message}` }
        : { tone: 'info', title: 'Approved (not executed)', message: r.message })
    } catch (err) {
      const code = err instanceof ApiError ? err.code : 'error'
      const msg = err instanceof Error ? err.message : 'Approval failed.'
      setResult({
        tone: code.startsWith('action_executed') || code.startsWith('action_approved') || code === 'action_stale' ? 'muted' : 'blocked',
        title: CODE_TITLES[code] ?? (err instanceof ApiError && err.status === 0 ? 'Backend unreachable' : 'Not approved'),
        message: msg,
      })
    }
    setStep('done') // the button stays disabled; the card re-renders from the backend's new status
    await onDecided()
  }

  return (
    <article className={`approval ${pending ? 'approval-pending' : 'approval-closed'}`} aria-labelledby={`appr-${action.action_id}`}>
      <div className="approval-top">
        <div>
          <p className="eyebrow">{kindLabel(action)} · Ticket #{action.ticket_id ?? '—'}</p>
          <h3 id={`appr-${action.action_id}`}>
            {action.kind === 'ticket_resolution' ? `Resolve ticket #${action.ticket_id}` : action.amount !== null ? money(action.amount) : 'Purchase request (no amount recorded)'}
            {action.payee && <span className="approval-payee"> to {action.payee}</span>}
          </h3>
        </div>
        <Pill value={action.status} />
      </div>
      <p>{action.description}</p>
      <dl className="approval-facts">
        {action.account_name && <><dt>From account</dt><dd>{action.account_name}</dd></>}
        {action.balance_after_at_preparation !== null && <><dt>Balance after (at prep)</dt><dd>{money(action.balance_after_at_preparation)}</dd></>}
        <dt>Prepared by</dt>
        <dd className="prep">{prep && <AgentAvatar meta={prep} size={20} />} {prep?.name ?? action.prepared_by} · {dateTime(action.created_at)}</dd>
        {action.approved_by && <><dt>Decided by</dt><dd>{action.approved_by}</dd></>}
        {action.payment_id !== null && <><dt>Payment record</dt><dd>#{action.payment_id}</dd></>}
        {action.balance_after !== null && <><dt>Balance after payment</dt><dd>{money(action.balance_after)}</dd></>}
      </dl>
      {action.blockers.length > 0 && <ul className="ticks ticks-blocked small">{action.blockers.map((b, i) => <li key={i}>{b}</li>)}</ul>}
      {action.note && <p className="small muted">{action.note}</p>}
      {undoneByReset && <p className="small reset-note">The working database was reset after this payment, so its effect on the books has been undone.</p>}

      {result && (
        <div className={`result result-${result.tone}`} role="status">
          <strong>{result.title}.</strong> {result.message}
        </div>
      )}

      {pending && step === 'idle' && (
        <button type="button" className="btn btn-approve" onClick={() => setStep('confirm')}>
          Review &amp; approve…
        </button>
      )}

      {pending && (step === 'confirm' || step === 'submitting') && (
        <form className="confirm-box" onSubmit={submit}>
          <p className="confirm-warn">
            {action.kind === 'ticket_resolution'
              ? <>This will <strong>mark ticket #{action.ticket_id} resolved</strong> in the working database. The Boss Agent reported its work complete; no money moves.</>
              : action.kind === 'payment'
              ? <>This will <strong>execute a real payment of {money(action.amount)}</strong> from <strong>{action.account_name}</strong> in the working database. The backend re-checks the amount and cash first and will refuse it if funds are insufficient.</>
              : <>This records your approval of the purchase. The system will <strong>not</strong> contact the vendor; a person must place the order.</>}
          </p>
          <label htmlFor={`approver-${action.action_id}`}>Your name (recorded as approver)</label>
          <input
            id={`approver-${action.action_id}`}
            value={approver}
            onChange={e => setApprover(e.target.value)}
            required
            maxLength={100}
            autoComplete="name"
            disabled={step === 'submitting'}
          />
          <div className="confirm-actions">
            <button type="button" className="btn" onClick={() => setStep('idle')} disabled={step === 'submitting'}>Cancel</button>
            <button type="submit" className="btn btn-approve" disabled={!approver.trim() || step === 'submitting'}>
              {step === 'submitting' ? 'Submitting…' : action.kind === 'payment' ? `Confirm & pay ${money(action.amount)}` : action.kind === 'ticket_resolution' ? 'Confirm: mark resolved' : 'Confirm approval'}
            </button>
          </div>
        </form>
      )}
    </article>
  )
}

export function ApprovalPanel({ actions, loading, error, onRetry, onDecided, lastResetAt }: Props) {
  const [results, setResults] = useState<Record<string, Result>>({})
  const card = (a: PreparedAction) => (
    <ApprovalCard key={a.action_id} action={a} onDecided={onDecided} result={results[a.action_id]}
      undoneByReset={a.status === 'executed' && !!lastResetAt && a.updated_at < lastResetAt}
      setResult={r => setResults(prev => ({ ...prev, [a.action_id]: r }))} />
  )
  const pending = actions.filter(a => a.status === 'pending_human_approval')
  const history = actions.filter(a => a.status !== 'pending_human_approval')
    .sort((x, y) => y.updated_at.localeCompare(x.updated_at)) // most recent decision first
  if (!error && actions.length === 0) return null

  return (
    <section className={`card approvals ${pending.length ? 'approvals-attention' : ''}`} aria-labelledby="approvals-heading">
      <h2 id="approvals-heading">
        {pending.length ? `Human approval needed (${pending.length})` : 'Approval history'}
      </h2>
      {pending.length > 0 && (
        <p className="muted small">Agents can prepare actions but cannot execute them. Nothing happens until you confirm.</p>
      )}
      {error && (
        <div className="inline-error" role="alert"><p>{error}</p><button type="button" className="btn btn-small" onClick={onRetry}>Retry</button></div>
      )}
      {loading && actions.length === 0 && <p className="muted small">Loading approvals…</p>}
      <div className="approval-list">
        {pending.map(card)}
      </div>
      {history.length > 0 && (
        <details className="history" open={pending.length === 0}>
          <summary>Decided and closed actions ({history.length})</summary>
          <div className="approval-list">
            {history.map(card)}
          </div>
        </details>
      )}
    </section>
  )
}
