import { DESK_STATUS_LABEL, type DeskStatus } from '../format'

export function StatusBadge({ status }: { status: DeskStatus }) {
  return (
    <span className={`badge badge-${status}`}>
      {status === 'running' && <span className="pulse" aria-hidden="true" />}
      {DESK_STATUS_LABEL[status]}
    </span>
  )
}

const TONE: Record<string, string> = {
  pending_human_approval: 'approval', executing: 'running', executed: 'resolved', approved: 'info',
  blocked: 'blocked', failed: 'blocked', stale: 'muted',
  succeeded: 'resolved', partial: 'approval', needs_human_approval: 'approval',
  ok: 'resolved', not_found_or_failed: 'blocked', refused: 'blocked', started: 'info',
  completed: 'resolved', stopped: 'blocked', accepted: 'info', reset: 'info',
}

const LABEL: Record<string, string> = {
  pending_human_approval: 'Awaiting approval', executing: 'Executing', executed: 'Executed', approved: 'Approved',
  blocked: 'Blocked', failed: 'Failed', stale: 'Stale', needs_human_approval: 'Needs approval',
  not_found_or_failed: 'Not found', approved_not_executed: 'Approved (not executed)',
}

/** Small pill for raw backend status strings (action, result, or event outcome). */
export function Pill({ value }: { value: string | null | undefined }) {
  if (!value) return null
  const tone = TONE[value] ?? 'muted'
  return <span className={`pill pill-${tone}`}>{LABEL[value] ?? value.replace(/_/g, ' ')}</span>
}
