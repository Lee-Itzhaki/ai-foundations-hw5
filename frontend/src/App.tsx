import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { AgentEvent, CashBalance, HealthResponse, PreparedAction, Ticket } from './api/types'
import { ApiError, api, describeError } from './api/client'
import { deskStatus, latestOutcome, type DeskStatus } from './format'
import { Header } from './components/Header'
import { TicketNav } from './components/TicketNav'
import { TicketWorkspace, type RunUiState } from './components/TicketWorkspace'
import { ActivityFeed } from './components/ActivityFeed'
import { RunSummary } from './components/RunSummary'
import { ApprovalPanel } from './components/ApprovalPanel'
import { ResetControl } from './components/ResetControl'

/** Run `fn` now and then every `ms` while `enabled`. Always calls the latest `fn`. */
function usePolling(fn: () => void, ms: number, enabled = true) {
  const ref = useRef(fn)
  useEffect(() => { ref.current = fn })
  useEffect(() => {
    if (!enabled) return
    ref.current()
    const id = window.setInterval(() => ref.current(), ms)
    return () => window.clearInterval(id)
  }, [ms, enabled])
}

const RUNS_KEY = 'cc-runs' // ticketId -> runId, so a page reload keeps following an active run

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)

  const [tickets, setTickets] = useState<Ticket[]>([])
  const [shopDate, setShopDate] = useState<string | null>(null)
  const [ticketsLoading, setTicketsLoading] = useState(true)
  const [ticketsError, setTicketsError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(
    () => Number(new URLSearchParams(location.search).get('ticket')) || Number(localStorage.getItem('cc-selected')) || null)

  const [cash, setCash] = useState<CashBalance | null>(null)
  const [cashError, setCashError] = useState<string | null>(null)
  const [cashFlash, setCashFlash] = useState(false)

  const [actions, setActions] = useState<PreparedAction[]>([])
  const [actionsLoading, setActionsLoading] = useState(true)
  const [actionsError, setActionsError] = useState<string | null>(null)

  const [allEvents, setAllEvents] = useState<AgentEvent[]>([])
  const [feed, setFeed] = useState<AgentEvent[]>([])
  const [feedLoading, setFeedLoading] = useState(true)
  const [feedError, setFeedError] = useState<string | null>(null)
  const [scope, setScope] = useState<'run' | 'ticket'>('run')

  const [runs, setRuns] = useState<Record<number, RunUiState>>({})
  const [refreshing, setRefreshing] = useState(false)

  // ---------------------------------------------------------------- loaders
  const loadHealth = useCallback(async () => {
    try { setHealth(await api.health()); setHealthError(null) } catch (e) { setHealthError(describeError(e)) }
  }, [])

  const loadTickets = useCallback(async () => {
    try {
      const r = await api.tickets()
      setTickets(r.tickets)
      setShopDate(r.shop_date)
      setTicketsError(null)
      setSelectedId(cur => (cur && r.tickets.some(t => t.id === cur) ? cur : r.tickets[0]?.id ?? null))
    } catch (e) { setTicketsError(describeError(e)) } finally { setTicketsLoading(false) }
  }, [])

  const prevBalance = useRef<number | null>(null)
  const loadCash = useCallback(async () => {
    try {
      const c = await api.checking()
      if (prevBalance.current !== null && prevBalance.current !== c.balance) {
        setCashFlash(true)
        window.setTimeout(() => setCashFlash(false), 1600)
      }
      prevBalance.current = c.balance
      setCash(c)
      setCashError(null)
    } catch (e) { setCashError(describeError(e)) }
  }, [])

  const loadActions = useCallback(async () => {
    try { setActions((await api.approvals()).actions); setActionsError(null) } catch (e) { setActionsError(describeError(e)) } finally { setActionsLoading(false) }
  }, [])

  const loadAllEvents = useCallback(async () => {
    try { setAllEvents((await api.events({ limit: 1000 })).events) } catch { /* feed shows its own error */ }
  }, [])

  // Latest run per ticket: from this session's runs, else from the audit trail.
  const latestRunId = useCallback((ticketId: number): string | undefined => {
    const own = runs[ticketId]?.run?.run_id
    if (own) return own
    for (let i = allEvents.length - 1; i >= 0; i--) {
      const e = allEvents[i]
      if (e.ticket_id === ticketId && e.event === 'database_reset') return undefined
      if (e.ticket_id === ticketId && e.event === 'run_started' && e.run_id) return e.run_id
    }
    return undefined
  }, [runs, allEvents])

  const selectedRunId = selectedId !== null ? latestRunId(selectedId) : undefined
  const effectiveScope = scope === 'run' && selectedRunId ? 'run' : 'ticket'

  const loadFeed = useCallback(async () => {
    if (selectedId === null) return
    try {
      const r = effectiveScope === 'run' && selectedRunId
        ? await api.events({ run_id: selectedRunId, limit: 500 })
        : await api.events({ ticket_id: selectedId, limit: 300 })
      setFeed(r.events)
      setFeedError(null)
    } catch (e) { setFeedError(describeError(e)) } finally { setFeedLoading(false) }
  }, [selectedId, selectedRunId, effectiveScope])

  const refreshAll = useCallback(async () => {
    setRefreshing(true)
    await Promise.all([loadHealth(), loadTickets(), loadCash(), loadActions(), loadAllEvents(), loadFeed()])
    setRefreshing(false)
  }, [loadHealth, loadTickets, loadCash, loadActions, loadAllEvents, loadFeed])

  // ---------------------------------------------------------------- polling
  const anyRunning = Object.values(runs).some(r => r.phase === 'running' || r.phase === 'starting')
  const selectedRunning = selectedId !== null && (runs[selectedId]?.phase === 'running' || runs[selectedId]?.phase === 'starting')
  const hasPending = actions.some(a => a.status === 'pending_human_approval')

  usePolling(loadHealth, 10_000)
  usePolling(loadTickets, anyRunning ? 4_000 : 15_000)
  usePolling(loadCash, 30_000)
  usePolling(loadActions, anyRunning || hasPending ? 4_000 : 15_000)
  usePolling(loadAllEvents, anyRunning ? 3_000 : 15_000)
  usePolling(loadFeed, selectedRunning ? 2_000 : 10_000, selectedId !== null)

  // When the backend comes back after being unreachable, reload everything at once.
  const wasDown = useRef(false)
  useEffect(() => {
    if (healthError) wasDown.current = true
    else if (health && wasDown.current) { wasDown.current = false; refreshAll() }
  }, [health, healthError, refreshAll])

  useEffect(() => { setFeedLoading(true); setFeed([]) }, [selectedId, effectiveScope])
  useEffect(() => { if (selectedId !== null) localStorage.setItem('cc-selected', String(selectedId)) }, [selectedId])

  // Resume following runs started before a page reload.
  useEffect(() => {
    const saved = JSON.parse(sessionStorage.getItem(RUNS_KEY) ?? '{}') as Record<string, string>
    for (const [tid, runId] of Object.entries(saved)) {
      api.run(runId).then(
        run => setRuns(p => ({ ...p, [Number(tid)]: { phase: run.status === 'running' ? 'running' : run.status, run } })),
        () => { /* server no longer tracks it; the audit trail still has its events */ },
      )
    }
  }, [])

  // Poll each running run until the backend reports it finished.
  const runningIds = Object.entries(runs).filter(([, r]) => r.phase === 'running' && r.run).map(([t, r]) => [Number(t), r.run!.run_id] as const)
  const runningKey = runningIds.map(([t, id]) => `${t}:${id}`).join(',')
  useEffect(() => {
    if (!runningIds.length) return
    const id = window.setInterval(async () => {
      for (const [tid, runId] of runningIds) {
        try {
          const run = await api.run(runId)
          if (run.status !== 'running') {
            setRuns(p => ({ ...p, [tid]: { phase: run.status, run } }))
            await Promise.all([loadTickets(), loadActions(), loadAllEvents(), loadCash()])
          } else {
            setRuns(p => ({ ...p, [tid]: { ...p[tid], run } }))
          }
        } catch (e) {
          setRuns(p => ({ ...p, [tid]: { ...p[tid], phase: 'failed', error: describeError(e), errorCode: e instanceof ApiError ? e.code : undefined } }))
        }
      }
    }, 2_000)
    return () => window.clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runningKey])

  // ---------------------------------------------------------------- actions
  async function startRun(ticketId: number) {
    const cur = runs[ticketId]?.phase
    if (cur === 'starting' || cur === 'running') return // never start the same ticket twice
    setRuns(p => ({ ...p, [ticketId]: { phase: 'starting' } }))
    setScope('run')
    try {
      const run = await api.runTicket(ticketId)
      setRuns(p => ({ ...p, [ticketId]: { phase: 'running', run } }))
      const saved = JSON.parse(sessionStorage.getItem(RUNS_KEY) ?? '{}')
      sessionStorage.setItem(RUNS_KEY, JSON.stringify({ ...saved, [ticketId]: run.run_id }))
      loadAllEvents()
    } catch (e) {
      setRuns(p => ({ ...p, [ticketId]: { phase: 'failed', error: describeError(e), errorCode: e instanceof ApiError ? e.code : undefined } }))
    }
  }

  const afterDecision = useCallback(async () => {
    await Promise.all([loadActions(), loadCash(), loadAllEvents(), loadFeed(), loadTickets()])
  }, [loadActions, loadCash, loadAllEvents, loadFeed, loadTickets])

  const afterReset = useCallback(async () => {
    setRuns({})
    sessionStorage.removeItem(RUNS_KEY)
    await refreshAll()
  }, [refreshAll])

  // ---------------------------------------------------------------- derived
  const actionsByTicket = useMemo(() => {
    const m: Record<number, PreparedAction[]> = {}
    for (const a of actions) if (a.ticket_id !== null) (m[a.ticket_id] ??= []).push(a)
    return m
  }, [actions])

  const statuses = useMemo(() => {
    const s: Record<number, DeskStatus> = {}
    for (const t of tickets) s[t.id] = deskStatus(t, runs[t.id]?.run, actionsByTicket[t.id] ?? [], latestOutcome(allEvents, t.id))
    for (const t of tickets) if (runs[t.id]?.phase === 'starting') s[t.id] = 'running'
    return s
  }, [tickets, runs, actionsByTicket, allEvents])

  const selected = tickets.find(t => t.id === selectedId) ?? null
  const selectedActions = actions.filter(a => a.ticket_id === selectedId)
  const runEvents = selectedRunId ? allEvents.filter(e => e.run_id === selectedRunId) : []
  const pendingCount = actions.filter(a => a.status === 'pending_human_approval').length
  const lastResetAt = [...allEvents].reverse().find(e => e.event === 'database_reset')?.timestamp ?? null

  return (
    <div className="app">
      <a href="#ticket-panel" className="skip-link">Skip to ticket</a>
      <Header
        health={health} healthError={healthError} cash={cash} cashError={cashError} cashFlash={cashFlash}
        shopDate={shopDate ?? health?.shop_date ?? null} pendingCount={pendingCount}
        onRefresh={refreshAll} refreshing={refreshing}
      />

      {healthError && (
        <div className="banner-error" role="alert">
          <strong>Can't reach the backend.</strong> {healthError} Start it from <code>backend/</code> with <code>uvicorn main:app --reload --port 8000</code>.
          <button type="button" className="btn btn-small" onClick={refreshAll}>Retry</button>
        </div>
      )}

      <div className="layout">
        <aside className="sidebar">
          <TicketNav
            tickets={tickets} statuses={statuses} selectedId={selectedId} onSelect={setSelectedId}
            loading={ticketsLoading} error={ticketsError} onRetry={loadTickets}
          />
          <ResetControl onReset={afterReset} disabled={anyRunning || !!healthError} />
        </aside>

        <main id="ticket-panel" role="tabpanel" aria-labelledby={selected ? `ticket-tab-${selected.id}` : undefined} className="workspace" tabIndex={-1}>
          {!selected && !ticketsLoading && !ticketsError && <div className="card empty"><p>Select a ticket to begin.</p></div>}
          {selected && (
            <>
              <TicketWorkspace
                ticket={selected} status={statuses[selected.id] ?? 'open'} runState={runs[selected.id] ?? { phase: 'idle' }}
                health={health} backendDown={!!healthError} onRun={() => startRun(selected.id)}
              />
              <ApprovalPanel actions={selectedActions} loading={actionsLoading} error={actionsError} onRetry={loadActions} onDecided={afterDecision} lastResetAt={lastResetAt} />
              <RunSummary ticketId={selected.id} run={runs[selected.id]?.run} events={runEvents} />
            </>
          )}
        </main>

        {selected && (
          <div className="activity-col">
            <ActivityFeed
              events={feed} scope={effectiveScope} onScope={setScope} hasRun={!!selectedRunId}
              live={selectedRunning} loading={feedLoading} error={feedError} onRetry={loadFeed}
            />
          </div>
        )}
      </div>
    </div>
  )
}
