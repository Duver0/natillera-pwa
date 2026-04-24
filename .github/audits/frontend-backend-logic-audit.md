# Frontend–Backend Logic Audit
**Date:** 2026-04-23  
**Auditor:** ASDD Orchestrator  
**Status:** COMPLETE

---

## 1. Duplications Found

### ACCEPTABLE (pure display — no action required)

| File | Line | Pattern | Verdict |
|------|------|---------|---------|
| `frontend/src/pages/ClientDetailPage.tsx` | 156 | `credit.pending_capital.toFixed(2)` | ACCEPTABLE — currency display formatting |
| `frontend/src/pages/ClientDetailPage.tsx` | 205 | `inst.expected_value.toFixed(2)` | ACCEPTABLE — currency display formatting |
| `frontend/src/pages/ClientDetailPage.tsx` | 232 | `s.contribution_amount.toFixed(2)` | ACCEPTABLE — currency display formatting |
| `frontend/src/pages/ClientDetailPage.tsx` | 252 | `evt.amount.toFixed(2)` | ACCEPTABLE — currency display formatting |
| `frontend/src/pages/ClientDetailPage.tsx` | 248 | `new Date(evt.created_at).toLocaleDateString()` | ACCEPTABLE — date formatting |
| `frontend/src/pages/ClientDetailPage.tsx` | 48 | `parseFloat(paymentAmount)` | ACCEPTABLE — UX input parsing, backend re-validates |
| `frontend/src/pages/ClientDetailPage.tsx` | 55–59 | `parseFloat(creditForm.initial_capital / annual_interest_rate)` | ACCEPTABLE — form input conversion only |

### CRITICAL (none found)

**No financial calculations duplicating backend formulas were found in any frontend file.**

The frontend contains ZERO instances of:
- Interest computation (`capital * rate / periods`)
- Principal portion division (`capital / remaining_periods`)
- Savings interest calculation
- Mora detection logic
- Payment allocation or breakdown logic
- Installment generation logic
- Debt aggregation formulas

Mora status is consumed from `credit.mora` and `credit.mora_since` — fields computed by `CreditService._refresh_mora()` on every `GET /credits/:id`. The frontend renders these fields; it does not derive them.

---

## 2. Delete-from-Frontend List

**Nothing to delete.** No critical duplications exist.

---

## 3. Move-to-Backend List

No logic needs to be moved. The current architecture is already correct:
- `backend/app/utils/calculations.py` — single source of truth for all formulas
- `backend/app/services/credit_service.py` — mora recalculated on every read
- `backend/app/services/payment_service.py` — payment allocation fully server-side

---

## 4. API Contracts — Gaps to Close

The frontend currently lacks precomputed summary fields that would prevent any future temptation to add frontend math. The following extensions are recommended:

### 4.1 `GET /api/v1/credits/:id` — extend CreditResponse

```typescript
interface CreditResponse {
  id: string
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

  // NEW — precomputed summary fields
  interest_due_current_period: number      // calculate_period_interest(pending_capital, rate, periodicity)
  overdue_interest_total: number           // sum(interest_portion - paid_toward_interest) for overdue installments
  overdue_capital_total: number            // sum(principal_portion - paid_toward_principal) for overdue installments
  overdue_installments_count: number
  next_installment: {
    id: string
    expected_date: string
    interest_portion: number
    principal_portion: number
    total: number
  } | null
  mora_status: {
    in_mora: boolean
    since_date: string | null
  }
}
```

### 4.2 `GET /api/v1/clients/:id` — extend ClientResponse

```typescript
interface ClientResponse {
  id: string
  first_name: string
  last_name: string
  phone: string
  document_id?: string
  address?: string
  notes?: string
  created_at: string
  updated_at: string

  // NEW — precomputed aggregates
  total_debt: number          // sum(pending_capital) for all ACTIVE credits
  mora_count: number          // count of ACTIVE credits where mora = true
  active_credits_count: number
}
```

### 4.3 `GET /api/v1/savings?client_id=:id` — add summary

```typescript
interface SavingsSummaryResponse {
  contributions: SavingsContribution[]

  // NEW — precomputed totals
  summary: {
    total_contributions: number
    projected_interest: number          // calculate_savings_interest(total, rate)
    projected_payout: number            // total_contributions + projected_interest
    savings_rate: number
  }
}
```

### 4.4 `POST /api/v1/payments/preview` — NEW endpoint

```typescript
// Request
interface PaymentPreviewRequest {
  credit_id: string
  amount: number
}

// Response — lets UI show breakdown before confirming
interface PaymentPreviewResponse {
  total_amount: number
  breakdown: Array<{
    type: 'OVERDUE_INTEREST' | 'OVERDUE_PRINCIPAL' | 'FUTURE_PRINCIPAL'
    amount: number
    installment_id: string
    installment_period_number: number
  }>
  remaining_after_payment: number
  new_pending_capital: number
  credit_will_close: boolean
}
```

---

## 5. Final Architecture Rules

| Rule | Enforcement |
|------|-------------|
| All interest, mora, debt, and payment allocation logic lives exclusively in `backend/app/utils/calculations.py` and the service layer | No exceptions |
| Frontend formats numbers with `Intl.NumberFormat` or `.toFixed(2)` for display only | Never derive financial values |
| Frontend formats dates with `toLocaleDateString()` or similar for display only | Never compute date differences for mora |
| Frontend may parse user input with `parseFloat()` / `parseInt()` for form submission | Backend re-validates all inputs |
| `POST /payments` returns full `applied_to` breakdown — frontend renders it, does not compute it | If frontend needs a preview, call `POST /payments/preview` |
| `GET /credits/:id` always returns fresh mora status — frontend reads `credit.mora` | Never derive mora from `expected_date` comparisons in frontend |
| Backend response shapes must include all precomputed summary fields listed in Section 4 | Prevents future drift |

---

## Summary

**CRITICAL dups found:** 0  
**ACCEPTABLE display patterns:** 7 (all `.toFixed(2)` or date formatting)  
**Files patched:** 0 (no action required)  
**New endpoints to add:** 1 (`POST /payments/preview`)  
**Endpoints to extend:** 3 (`GET /credits/:id`, `GET /clients/:id`, `GET /savings`)  
**Architecture gap:** `CreditResponse` and `ClientResponse` do not yet expose precomputed aggregate fields — this is the only risk vector for future frontend drift.
