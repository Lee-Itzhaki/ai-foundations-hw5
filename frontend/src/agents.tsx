// Agent avatar and tag components.
import { agentMeta, type AgentMeta } from './agentMeta'

function Glyph({ k }: { k: AgentMeta['key'] }) {
  const p = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }
  switch (k) {
    case 'boss': // compass: sets direction
      return (<><circle cx="12" cy="12" r="8" {...p} /><path d="M15 9l-2 4-4 2 2-4z" {...p} /></>)
    case 'inventory': // box
      return (<><path d="M4 8l8-4 8 4v8l-8 4-8-4z" {...p} /><path d="M4 8l8 4 8-4M12 12v8" {...p} /></>)
    case 'accounting': // ledger
      return (<><rect x="5" y="4" width="14" height="16" rx="2" {...p} /><path d="M9 9h6M9 13h6M9 17h3" {...p} /></>)
    case 'facilities': // storefront
      return (<><path d="M4 10l2-5h12l2 5M5 10v9h14v-9" {...p} /><path d="M10 19v-5h4v5" {...p} /></>)
    case 'customer_service': // speech bubble
      return (<><path d="M5 6h14v9H10l-4 3v-3H5z" {...p} /><path d="M9 10h6" {...p} /></>)
    case 'human':
      return (<><circle cx="12" cy="9" r="3.2" {...p} /><path d="M6 19c1-3.5 3.3-5 6-5s5 1.5 6 5" {...p} /></>)
    default:
      return (<><rect x="5" y="6" width="14" height="10" rx="2" {...p} /><path d="M9 20h6M12 16v4" {...p} /></>)
  }
}

export function AgentAvatar({ meta, size = 32, dim = false }: { meta: AgentMeta; size?: number; dim?: boolean }) {
  return (
    <span
      className="agent-avatar"
      style={{ width: size, height: size, color: meta.color, background: meta.tint, borderColor: meta.color, opacity: dim ? 0.45 : 1 }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 24 24" width={size * 0.6} height={size * 0.6}><Glyph k={meta.key} /></svg>
    </span>
  )
}

export function AgentTag({ agent, event }: { agent: string | null | undefined; event?: string | null }) {
  const m = agentMeta(agent, event)
  return (
    <span className="agent-tag" style={{ color: m.color, background: m.tint }}>
      {m.name}
    </span>
  )
}
