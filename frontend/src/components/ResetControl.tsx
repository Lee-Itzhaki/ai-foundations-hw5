import { useRef, useState } from 'react'
import type { ResetResponse } from '../api/types'
import { api, describeError } from '../api/client'
import { money } from '../format'

export function ResetControl({ onReset, disabled }: { onReset: () => Promise<void>; disabled: boolean }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<ResetResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function confirmReset() {
    setBusy(true)
    setError(null)
    try {
      const r = await api.reset()
      setResult(r)
      dialog.current?.close()
      await onReset()
    } catch (e) {
      setError(describeError(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="maintenance" aria-labelledby="maint-heading">
      <div>
        <h2 id="maint-heading" className="section-label">Maintenance</h2>
        <p className="small muted">Restore the working database (<code>campus_customs_new.db</code>) to the original values. The original file is never changed.</p>
        {result && (
          <p className="small ok-text" role="status">
            Reset complete. Checking is back to {money(result.checking_balance)}; {result.invalidated_pending_actions} pending action(s) were marked stale.
          </p>
        )}
      </div>
      <button type="button" className="btn btn-danger-outline" onClick={() => { setError(null); dialog.current?.showModal() }} disabled={disabled}>
        Reset working database…
      </button>

      <dialog ref={dialog} className="modal" aria-labelledby="reset-title" onCancel={e => busy && e.preventDefault()}>
        <h2 id="reset-title">Reset the working database?</h2>
        <p>This copies <code>data/campus_customs.db</code> over <code>data/campus_customs_new.db</code>, restoring every ticket, invoice, lease, payment, and the checking balance to their <strong>original values</strong>.</p>
        <ul className="ticks small">
          <li>Any payments executed from this desk are undone.</li>
          <li>Pending approvals become stale and can no longer be approved.</li>
          <li>The audit trail is kept.</li>
        </ul>
        {error && <p className="err-text" role="alert">{error}</p>}
        <div className="confirm-actions">
          <button type="button" className="btn" onClick={() => dialog.current?.close()} disabled={busy} autoFocus>Cancel</button>
          <button type="button" className="btn btn-danger" onClick={confirmReset} disabled={busy}>
            {busy ? 'Resetting…' : 'Yes, reset to original'}
          </button>
        </div>
      </dialog>
    </section>
  )
}
