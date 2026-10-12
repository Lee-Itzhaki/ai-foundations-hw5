import { useEffect, useRef } from 'react'
import type { AgentEvent, AgentName } from '../api/types'
import { AGENT_ORDER, AGENTS, agentMeta } from '../agentMeta'
import { AgentAvatar, AgentTag } from '../agents'
import { cleanSummary, time } from '../format'
import { Pill } from './StatusBadge'

interface Props {
  events: AgentEvent[]
  scope: 'run' | 'ticket'
  onScope: (s: 'run' | 'ticket') => void
  hasRun: boolean
  live: boolean
  loading: boolean
  error: string | null
  onRetry: () => void
}

function argsText(args: Record<string, unknown> | null): string {
  if (!args) return ''
  return Object.entries(args).map(([k, v]) => `${k}=${typeof v === 'string' ? `"${v}"` : JSON.stringify(v)}`).join(', ')
}

/** One sentence describing a structured audit event. Nothing here is model reasoning. */
function describe(e: AgentEvent): { title: React.ReactNode; detail?: string; mono?: boolean } {
  const name = (a: string | null) => agentMeta(a).name
  switch (e.event) {
    case 'run_started':
      return { title: <>Started the run: {e.action}</> }
    case 'api_request':
      return { title: <>Desk request: {e.action}</>, detail: e.stop_or_continue ?? undefined }
    case 'mcp_tool_call':
      return {
        title: <>Called MCP tool <code>{e.mcp_tool}</code>{e.tool_args && Object.keys(e.tool_args).length > 0 && <span className="args">({argsText(e.tool_args)})</span>}</>,
        detail: e.error ?? e.result_summary ?? undefined,
        mono: !e.error,
      }
    case 'delegation':
      if (e.outcome === 'started')
        return { title: <>Delegated to <strong>{name(e.delegation_target)}</strong></>, detail: e.action ?? undefined }
      return { title: <>Reported back to <strong>{name(e.delegation_target)}</strong></>, detail: cleanSummary(e.result_summary) || e.error || undefined }
    case 'delegation_refused':
      return { title: <>Delegation to <strong>{name(e.delegation_target)}</strong> refused</>, detail: e.error ?? undefined }
    case 'agent_finished':
      return { title: <>Concluded ticket #{e.ticket_id}</>, detail: cleanSummary(e.result_summary) }
    case 'approval_requested':
      return { title: <>Prepared an action for human approval</>, detail: e.action ?? undefined }
    case 'approval_decision':
      return { title: <>Approval decision: {e.action}</>, detail: e.error ?? undefined }
    case 'output_rejected':
      return { title: <>Output rejected by a safety check</>, detail: e.error ?? undefined }
    case 'limit_reached':
      return { title: <>Limit reached</>, detail: e.error ?? e.stop_or_continue ?? undefined }
    case 'run_finished':
      return { title: <>Run finished</>, detail: e.stop_or_continue ?? undefined }
    case 'database_reset':
      return { title: <>Working database reset from the original</>, detail: e.result_summary ?? undefined }
    case 'error':
      return { title: <>Error</>, detail: e.error ?? undefined }
    default:
      return { title: <>{e.event ?? 'event'}</>, detail: e.result_summary ?? undefined }
  }
}

export function AgentRoster({ events, live }: { events: AgentEvent[]; live: boolean }) {
  const involved = new Set(events.map(e => e.agent).filter(Boolean) as string[])
  const last = [...events].reverse().find(e => e.agent && e.agent in AGENTS)?.agent
  return (
    <ul className="roster" aria-label="Agents in this view">
      {AGENT_ORDER.map((k: AgentName) => {
        const m = AGENTS[k]
        const on = involved.has(k)
        const active = live && last === k
        return (
          <li key={k} className={`roster-item ${on ? 'is-on' : ''} ${active ? 'is-active' : ''}`} style={{ ['--agent' as string]: m.color }}>
            <AgentAvatar meta={m} size={30} dim={!on} />
            <span className="roster-text">
              <span className="roster-name">{m.name}</span>
              <span className="roster-role">{active ? 'working…' : on ? 'took part' : m.role}</span>
            </span>
          </li>
        )
      })}
    </ul>
  )
}

export function ActivityFeed({ events, scope, onScope, hasRun, live, loading, error, onRetry }: Props) {
  const listRef = useRef<HTMLOListElement>(null)
  const count = events.length
  useEffect(() => {
    if (live && listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [count, live])

  return (
    <section className="card activity" aria-labelledby="activity-heading">
      <div className="activity-head">
        <h2 id="activity-heading">Agent activity {live && <span className="live-dot" aria-label="live">Live</span>}</h2>
        <div className="seg" role="group" aria-label="Activity scope">
          <button type="button" aria-pressed={scope === 'run'} disabled={!hasRun} onClick={() => onScope('run')}>Latest run</button>
          <button type="button" aria-pressed={scope === 'ticket'} onClick={() => onScope('ticket')}>All for ticket</button>
        </div>
      </div>

      <AgentRoster events={events} live={live} />

      {error && (
        <div className="inline-error" role="alert">
          <p>{error}</p>
          <button type="button" className="btn btn-small" onClick={onRetry}>Retry</button>
        </div>
      )}
      {!error && count === 0 && (
        <div className="empty">
          <p>{loading ? 'Loading activity…' : 'No agent activity yet for this ticket.'}</p>
          {!loading && <p className="muted small">Run the agent team to see each agent's delegations and MCP tool calls here.</p>}
        </div>
      )}

      <ol className="feed" ref={listRef} aria-live={live ? 'polite' : 'off'}>
        {events.map((e, i) => {
          const m = agentMeta(e.agent, e.event)
          const d = describe(e)
          return (
            <li key={`${e.run_id}-${e.step}-${i}`} className={`feed-item ev-${e.event}`} style={{ ['--agent' as string]: m.color }}>
              <AgentAvatar meta={m} size={28} />
              <div className="feed-body">
                <div className="feed-line">
                  <AgentTag agent={e.agent} event={e.event} />
                  <span className="feed-title">{d.title}</span>
                </div>
                {d.detail && <p className={`feed-detail ${d.mono ? 'mono' : ''}`}>{d.detail}</p>}
                <div className="feed-meta">
                  <span>{time(e.timestamp)}</span>
                  {e.step !== null && <span>step {e.step}</span>}
                  {e.delegation_depth !== null && <span>depth {e.delegation_depth}</span>}
                  <Pill value={e.outcome} />
                  {e.approval_pending && <span className="pill pill-approval">Approval pending</span>}
                </div>
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
