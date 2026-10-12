import type { AgentEvent, AgentName, RunStatus, TicketOutcome } from '../api/types'
import { AGENT_ORDER, AGENTS } from '../agentMeta'
import { AgentAvatar } from '../agents'
import { RESULT_LABEL, cleanSummary, money } from '../format'
import { Pill } from './StatusBadge'

interface Props {
  ticketId: number
  run: RunStatus | undefined
  events: AgentEvent[] // events for the run being summarized
}

interface AgentDigest {
  agent: AgentName
  tools: string[]
  conclusions: { text: string; status: string | null }[]
  delegatedTo: string[]
}

/** Build a per-agent digest strictly from backend audit events. */
function digest(events: AgentEvent[]): AgentDigest[] {
  const map = new Map<AgentName, AgentDigest>()
  const get = (a: AgentName) => {
    if (!map.has(a)) map.set(a, { agent: a, tools: [], conclusions: [], delegatedTo: [] })
    return map.get(a)!
  }
  for (const e of events) {
    if (!e.agent || !(e.agent in AGENTS)) continue
    const d = get(e.agent as AgentName)
    if (e.event === 'mcp_tool_call' && e.mcp_tool && !d.tools.includes(e.mcp_tool)) d.tools.push(e.mcp_tool)
    if (e.event === 'delegation' && e.outcome === 'started' && e.delegation_target) {
      const n = AGENTS[e.delegation_target as AgentName]?.name ?? e.delegation_target
      if (!d.delegatedTo.includes(n)) d.delegatedTo.push(n)
    }
    if (e.event === 'delegation' && e.outcome !== 'started')
      d.conclusions.push({ text: cleanSummary(e.result_summary) || e.error || '', status: e.outcome })
    if (e.event === 'agent_finished') d.conclusions.push({ text: cleanSummary(e.result_summary), status: e.outcome })
  }
  return AGENT_ORDER.filter(a => map.has(a)).map(a => map.get(a)!)
}

function OutcomeBanner({ outcome }: { outcome: TicketOutcome }) {
  const tone = outcome.status === 'succeeded' ? 'resolved' : outcome.status === 'blocked' || outcome.status === 'failed' ? 'blocked' : 'approval'
  return (
    <div className={`outcome outcome-${tone}`}>
      <p className="outcome-status">Boss's conclusion: <strong>{RESULT_LABEL[outcome.status]}</strong></p>
      <p>{outcome.summary}</p>
    </div>
  )
}

export function RunSummary({ ticketId, run, events }: Props) {
  const outcome = run?.report?.tickets.find(t => t.ticket_id === ticketId)
  // Without this session's report (e.g. after a reload), use the Boss's recorded conclusion.
  const finished = [...events].reverse().find(e => e.event === 'agent_finished' && e.agent === 'boss' && e.ticket_id === ticketId)
  const agents = digest(events)
  if (!run && agents.length === 0) return null
  if (run?.status === 'running') return null

  return (
    <section className="card summary" aria-labelledby="summary-heading">
      <h2 id="summary-heading">Run summary</h2>
      {run?.status === 'failed' && (
        <div className="outcome outcome-blocked" role="alert">
          <p className="outcome-status"><strong>The run did not finish.</strong></p>
          <p>{run.error ?? 'No error message was returned.'}</p>
        </div>
      )}
      {outcome && <OutcomeBanner outcome={outcome} />}
      {!outcome && finished && (
        <div className={`outcome outcome-${finished.outcome === 'succeeded' ? 'resolved' : finished.outcome === 'blocked' || finished.outcome === 'failed' ? 'blocked' : 'approval'}`}>
          <p className="outcome-status">Boss's conclusion: <strong>{RESULT_LABEL[finished.outcome as keyof typeof RESULT_LABEL] ?? finished.outcome}</strong></p>
          <p>{cleanSummary(finished.result_summary)}</p>
        </div>
      )}
      {!run && <p className="muted small">Showing the latest recorded run for this ticket from the audit trail (run <code>{events[0]?.run_id}</code>).</p>}

      {outcome && (outcome.blockers.length > 0 || outcome.human_decisions_needed.length > 0) && (
        <div className="summary-grid">
          {outcome.blockers.length > 0 && (
            <div>
              <h3>Blockers</h3>
              <ul className="ticks ticks-blocked">{outcome.blockers.map((b, i) => <li key={i}>{b}</li>)}</ul>
            </div>
          )}
          {outcome.human_decisions_needed.length > 0 && (
            <div>
              <h3>Decisions for a human</h3>
              <ul className="ticks ticks-approval">{outcome.human_decisions_needed.map((b, i) => <li key={i}>{b}</li>)}</ul>
            </div>
          )}
        </div>
      )}

      {agents.length > 0 && (
        <>
          <h3>What each agent did</h3>
          <ul className="agent-digests">
            {agents.map(d => {
              const m = AGENTS[d.agent]
              const last = d.conclusions[d.conclusions.length - 1]
              return (
                <li key={d.agent} className="digest" style={{ ['--agent' as string]: m.color }}>
                  <div className="digest-head">
                    <AgentAvatar meta={m} size={28} />
                    <strong>{m.name}</strong>
                    {last?.status && <Pill value={last.status} />}
                  </div>
                  {last?.text && <p>{last.text}</p>}
                  <p className="muted small">
                    {d.tools.length > 0 ? <>Tools: {d.tools.map(t => <span key={t}><code>{t}</code> </span>)}</> : 'No MCP tools called.'}
                    {d.delegatedTo.length > 0 && <> · Delegated to {d.delegatedTo.join(', ')}</>}
                  </p>
                </li>
              )
            })}
          </ul>
        </>
      )}

      {outcome && outcome.customer_drafts.length > 0 && (
        <>
          <h3>Customer drafts <span className="pill pill-muted">Not sent</span></h3>
          {outcome.customer_drafts.map((c, i) => (
            <article key={i} className="draft">
              <p className="small muted">To {c.recipient} · Subject: {c.subject}</p>
              <p className="draft-body">{c.body}</p>
            </article>
          ))}
        </>
      )}

      {outcome && outcome.payment_proposals.length > 0 && (
        <p className="small muted">
          Payment proposals in this run: {outcome.payment_proposals.map(p => `${p.payment_kind} #${p.reference_id} (${money(p.amount)}, ${p.status})`).join('; ')}. Approve them in the approval area above.
        </p>
      )}
      {run?.report && <p className="small muted">Stop reason: {run.report.stop_reason}</p>}
    </section>
  )
}
