// Identity data for the five agents (and the human/system actors in the audit trail).
import type { AgentName } from './api/types'

export interface AgentMeta {
  key: AgentName | 'human' | 'system'
  name: string
  role: string
  initials: string
  color: string // accent, >= 4.5:1 on white
  tint: string // light background
}

export const AGENTS: Record<AgentName, AgentMeta> = {
  boss: { key: 'boss', name: 'Boss', role: 'Coordinates the desk', initials: 'BO', color: '#00356B', tint: '#E6EDF5' },
  inventory: { key: 'inventory', name: 'Inventory', role: 'Stock, pricing & vendors', initials: 'IN', color: '#2D6A4F', tint: '#E7F2EC' },
  accounting: { key: 'accounting', name: 'Accounting', role: 'Invoices, cash & payments', initials: 'AC', color: '#8A5300', tint: '#FBF0DF' },
  facilities: { key: 'facilities', name: 'Facilities', role: 'Leases & the shop space', initials: 'FA', color: '#5B4699', tint: '#EFEBF8' },
  customer_service: { key: 'customer_service', name: 'Customer Service', role: 'Customer drafts', initials: 'CS', color: '#A3324F', tint: '#FAE9EE' },
}

export const AGENT_ORDER: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

const HUMAN: AgentMeta = { key: 'human', name: 'Human approver', role: 'You', initials: 'YOU', color: '#3F3A33', tint: '#EFEAE1' }
const SYSTEM: AgentMeta = { key: 'system', name: 'Desk system', role: 'Backend', initials: 'SYS', color: '#4A5560', tint: '#ECEFF2' }

export function agentMeta(agent: string | null | undefined, event?: string | null): AgentMeta {
  if (agent && agent in AGENTS) return AGENTS[agent as AgentName]
  if (event === 'approval_decision') return HUMAN
  return SYSTEM
}
