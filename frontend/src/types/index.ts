export interface User {
  id: string
  email: string
  first_name?: string
  last_name?: string
}

export interface AuthTokens {
  accessToken: string | null
  refreshToken: string | null
}

export interface Client {
  id: string
  user_id: string
  first_name: string
  last_name: string
  phone: string
  document_id?: string
  address?: string
  notes?: string
  created_at: string
  updated_at: string
  deleted_at?: string
  total_debt?: number
  mora_count?: number
}

export type Periodicity = 'DAILY' | 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY'
export type CreditStatus = 'ACTIVE' | 'CLOSED' | 'SUSPENDED'

export interface MoraStatus {
  in_mora: boolean
  since_date?: string
}

export interface Credit {
  id: string
  user_id: string
  client_id: string
  initial_capital: number
  pending_capital: number
  version: number
  periodicity: Periodicity
  annual_interest_rate: number
  status: CreditStatus
  start_date: string
  closed_date?: string
  next_period_date?: string
  mora: boolean
  mora_since?: string
  created_at: string
  updated_at: string
  // Precomputed fields from backend
  interest_due_current_period?: number
  overdue_interest_total?: number
  overdue_capital_total?: number
  next_installment?: Installment
  upcoming_installments?: Installment[]
  overdue_installments?: Installment[]
  mora_status?: MoraStatus
}

export interface ClientSummary {
  client_id: string
  active_credits_count: number
  total_pending_capital: number
  total_overdue: number
  mora_count: number
  savings_total: number
}

export interface UpdatedCreditSnapshot {
  pending_capital: string // Decimal string from backend
  mora: boolean
  version: number
}

export interface PaymentPreview {
  credit_id: string
  total_amount: string // Decimal string
  applied_to: PaymentAppliedTo[]
  unallocated: string // Decimal string
  updated_credit_snapshot: UpdatedCreditSnapshot
}

export interface PaymentResponse {
  payment_id: string
  credit_id: string
  total_amount: string // Decimal string
  applied_to: PaymentAppliedTo[]
  updated_credit_snapshot: UpdatedCreditSnapshot
}

export type InstallmentStatus = 'UPCOMING' | 'PARTIALLY_PAID' | 'PAID' | 'SUSPENDED'

export interface Installment {
  id: string
  user_id: string
  credit_id: string
  period_number: number
  expected_date: string
  expected_value: number
  principal_portion: number
  interest_portion: number
  paid_value: number
  is_overdue: boolean
  status: InstallmentStatus
  created_at: string
  paid_at?: string
}

export interface PaymentAppliedTo {
  type: 'OVERDUE_INTEREST' | 'OVERDUE_PRINCIPAL' | 'FUTURE_PRINCIPAL'
  amount: string // Decimal string from backend
  installment_id: string
}

export interface Payment {
  id: string
  user_id: string
  credit_id: string
  amount: number
  payment_date: string
  applied_to: PaymentAppliedTo[]
  notes?: string
  recorded_by: string
  created_at: string
}

export interface SavingsContribution {
  id: string
  user_id: string
  client_id: string
  contribution_amount: number
  contribution_date: string
  status: 'ACTIVE' | 'LIQUIDATED'
  liquidated_at?: string
  created_at: string
}

export interface SavingsLiquidation {
  id: string
  user_id: string
  client_id: string
  total_contributions: number
  interest_earned: number
  total_delivered: number
  interest_rate: number
  liquidation_date: string
  created_at: string
}

export type EventType =
  | 'CREDIT_CREATED'
  | 'CREDIT_CLOSED'
  | 'CREDIT_SUSPENDED'
  | 'INSTALLMENT_GENERATED'
  | 'PAYMENT_RECORDED'
  | 'SAVINGS_CONTRIBUTION'
  | 'SAVINGS_LIQUIDATION'
  | 'CLIENT_CREATED'
  | 'CLIENT_DELETED'

export interface HistoryEvent {
  id: string
  user_id: string
  event_type: EventType
  client_id: string
  credit_id?: string
  amount?: number
  description: string
  metadata?: Record<string, unknown>
  operator_id: string
  created_at: string
}
