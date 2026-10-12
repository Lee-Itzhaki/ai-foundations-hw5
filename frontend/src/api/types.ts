// TypeScript mirrors of the FastAPI response models in backend/main.py,
// backend/models.py and backend/actions.py. Keep these in sync with the backend.

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export type ResultStatus = 'succeeded' | 'partial' | 'needs_human_approval' | 'blocked' | 'failed'
export type ApprovalStatus = 'not_required' | 'pending_human_approval' | 'approved' | 'denied'

export interface ErrorBody {
  code: string
  message: string
  details?: unknown
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  working_db_present: boolean
  original_db_present: boolean
  mcp_reachable: boolean
  model_configured: boolean
  model: string
  shop_date: string | null
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  is_open: boolean
  notes: string | null
  created_at: string
}

export interface TicketList {
  count: number
  shop_date: string | null
  tickets: Ticket[]
}

export interface Evidence {
  mcp_tool: string
  fact: string
}

export interface PaymentProposal {
  payment_kind: 'vendor_invoice' | 'lease_rent'
  reference_id: number
  account_name: string
  amount: number
  payee: string
  balance_after_payment: number
  status: 'proposed' | 'blocked'
  approval_status: ApprovalStatus
  blockers: string[]
}

export interface CustomerDraft {
  ticket_id: number
  recipient: string
  subject: string
  body: string
  status: 'proposed'
  sent: false
}

export interface ProposedAction {
  action_type: 'restock_order' | 'price_quote' | 'facilities_task' | 'ticket_update' | 'other'
  description: string
  status: 'proposed' | 'blocked'
  approval_status: ApprovalStatus
  blockers: string[]
}

export interface ErrorInfo {
  code: string
  message: string
  recoverable: boolean
}

export interface DelegationRecord {
  source: AgentName
  target: AgentName
  depth: number
  task: string
  result_status: ResultStatus
}

export interface AgentResult {
  agent: AgentName
  ticket_id: number | null
  status: ResultStatus
  summary: string
  evidence: Evidence[]
  payment_proposals: PaymentProposal[]
  customer_drafts: CustomerDraft[]
  proposed_actions: ProposedAction[]
  delegations: DelegationRecord[]
  errors: ErrorInfo[]
  return_to_boss_reason: string | null
}

export interface TicketOutcome {
  ticket_id: number
  ticket_type: string
  status: ResultStatus
  summary: string
  evidence: Evidence[]
  specialist_results: AgentResult[]
  payment_proposals: PaymentProposal[]
  customer_drafts: CustomerDraft[]
  proposed_actions: ProposedAction[]
  blockers: string[]
  human_decisions_needed: string[]
}

export interface BossReport {
  shop_date: string | null
  tickets: TicketOutcome[]
  stop_reason: string
}

export interface RunStatus {
  run_id: string
  ticket_id: number
  status: 'running' | 'completed' | 'failed'
  started_at: string
  finished_at: string | null
  report: BossReport | null
  pending_action_ids: string[]
  error: string | null
}

export interface AgentEvent {
  timestamp: string | null
  run_id: string | null
  step: number | null
  event: string | null
  agent: string | null
  ticket_id: number | null
  action: string | null
  delegation_source: string | null
  delegation_target: string | null
  delegation_depth: number | null
  mcp_tool: string | null
  tool_args: Record<string, unknown> | null
  result_summary: string | null
  approval_status: string | null
  approval_pending: boolean
  outcome: string | null
  error: string | null
  stop_or_continue: string | null
}

export interface EventList {
  count: number
  total_in_trail: number
  events: AgentEvent[]
}

export type ActionStoredStatus =
  | 'pending_human_approval' | 'executing' | 'executed' | 'approved' | 'blocked' | 'failed' | 'stale'

export interface PreparedAction {
  action_id: string
  kind: 'payment' | 'purchase' | 'ticket_resolution'
  run_id: string
  ticket_id: number | null
  prepared_by: string
  description: string
  status: ActionStoredStatus
  created_at: string
  updated_at: string
  payment_kind: 'vendor_invoice' | 'lease_rent' | null
  reference_id: number | null
  account_name: string | null
  amount: number | null
  payee: string | null
  balance_after_at_preparation: number | null
  approved_by: string | null
  payment_id: number | null
  balance_after: number | null
  blockers: string[]
  note: string | null
}

export interface ActionList {
  count: number
  actions: PreparedAction[]
}

export interface ApproveRequest {
  approved_by: string
  confirm: true
}

export interface ApproveResponse {
  action: PreparedAction
  executed: boolean
  checking_balance: number | null
  message: string
}

export interface CashBalance {
  account: string
  balance: number
  as_of: string
  source: string
}

export interface ResetResponse {
  reset: boolean
  source: string
  target: string
  sha256: string
  original_unchanged: boolean
  invalidated_pending_actions: number
  checking_balance: number | null
  message: string
}
