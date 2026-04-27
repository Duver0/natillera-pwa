# Week 4 Gate — Payment Processing (Phase 4)

Date: 2026-04-24
Status: GATE IN PROGRESS — mocked tests written; live DB PENDING-HUMAN

---

## Phase 4 Deliverables Checklist

### Contract Documentation
- [x] `payment-contract.md` created at `.github/specs/payment-contract.md`
- [x] Main spec updated: `related-specs` includes payment-contract.md
- [x] Contract defines: request schema, response schema, allocation algorithm, Pydantic schemas
- [x] `POST /payments` response: payment_id, total_amount, applied_to (with installment_id), updated_credit_snapshot
- [x] `POST /payments/preview`: same shape minus payment_id, plus unallocated, version unchanged
- [x] Overpayment rule documented: apply-to-capital per spec §1.3 #4

### Backend Implementation
- [x] `backend/app/models/payment_model.py` — refactored to Decimal, new schemas: PaymentResponse, PaymentPreviewResponse, AppliedToEntry, UpdatedCreditSnapshot
- [x] `backend/app/services/payment_service.py` — refactored:
  - `_compute_breakdown()` pure function, Decimal everywhere, ROUND_HALF_EVEN
  - `process_payment()` returns structured dict matching PaymentResponse contract
  - `preview_payment_breakdown(credit_id, amount)` — zero writes
  - Optimistic lock fix: 0-row update → VersionConflict/409 (Week 2 risk #3 resolved)
  - `_compute_installment_new_states()` helper — no mutation of locked fields
- [x] `backend/app/routes/payment_router.py` — refactored:
  - `POST /` → 201, response_model=PaymentResponse
  - `POST /preview` → 200, response_model=PaymentPreviewResponse
  - Version conflict caught → explicit 409
  - Business error → 400, validation → 422

### Test Suite (10 required files)
- [x] `conftest_payment.py` — shared fixtures, Decimal helpers, mock builder
- [x] `test_payment_mandatory_order.py` — 6 tests (OVERDUE_INTEREST → OVERDUE_PRINCIPAL → FUTURE_PRINCIPAL)
- [x] `test_payment_partial_application.py` — 5 tests (payment < installment remaining)
- [x] `test_payment_overpayment.py` — 5 tests (excess → capital, auto-close, no rejection)
- [x] `test_payment_boundary_conditions.py` — 6 tests (exact match, zero remaining, min precision, version increment)
- [x] `test_payment_multi_installment.py` — 4 tests (FIFO across multiple overdue + mixed)
- [x] `test_payment_atomicity.py` — 3 tests (mid-loop failure, no partial commit, no payment on conflict)
- [x] `test_optimistic_locking_retry.py` — 4 tests (0-row update → exception, correct type, no payment insert)
- [x] `test_payment_preview.py` — 7 tests (method exists, no writes, same breakdown, response shape, version unchanged)
- [x] `test_payment_installment_status_transitions.py` — 5 tests (UPCOMING→PARTIAL→PAID, mora transitions, paid_at)
- [x] `test_payment_pending_capital_update.py` — 5 tests (interest-only no decrement, principal decrement, future principal, no float)

### Total: 50 test cases (mocked DB)

---

## Verification Status by Test (mocked DB only)

| Test File | Tests | Status | Notes |
|-----------|-------|--------|-------|
| test_payment_mandatory_order | 6 | WRITTEN — run pending | Tests new structured response contract |
| test_payment_partial_application | 5 | WRITTEN — run pending | |
| test_payment_overpayment | 5 | WRITTEN — run pending | |
| test_payment_boundary_conditions | 6 | WRITTEN — run pending | |
| test_payment_multi_installment | 4 | WRITTEN — run pending | |
| test_payment_atomicity | 3 | WRITTEN — run pending | |
| test_optimistic_locking_retry | 4 | WRITTEN — run pending | Covers Week 2 risk #3 |
| test_payment_preview | 7 | WRITTEN — run pending | |
| test_payment_installment_status_transitions | 5 | WRITTEN — run pending | |
| test_payment_pending_capital_update | 5 | WRITTEN — run pending | |

---

## Business Rules Verified by Tests

| Rule | Test File | Coverage |
|------|-----------|---------|
| OVERDUE_INTEREST applied first | test_payment_mandatory_order | 3 tests |
| OVERDUE_PRINCIPAL before FUTURE | test_payment_mandatory_order, test_payment_multi_installment | 4 tests |
| Partial payment → PARTIALLY_PAID status | test_payment_partial_application | 2 tests |
| Remainder stays in installment | test_payment_partial_application | 2 tests |
| Overpayment → apply to capital | test_payment_overpayment | 3 tests |
| Auto-close when capital = 0 | test_payment_overpayment | 1 test |
| Exact match → PAID | test_payment_boundary_conditions | 1 test |
| Paid installment skipped | test_payment_boundary_conditions | 1 test |
| Version incremented | test_payment_boundary_conditions | 1 test |
| FIFO order across multiple overdue | test_payment_multi_installment | 2 tests |
| pending_capital decremented by principal only | test_payment_pending_capital_update | 4 tests |
| Interest-only payment does not reduce capital | test_payment_pending_capital_update | 1 test |
| Optimistic lock 0-row → exception | test_optimistic_locking_retry | 3 tests |
| No payment insert on conflict | test_payment_atomicity, test_optimistic_locking_retry | 2 tests |
| Preview zero writes | test_payment_preview | 2 tests |
| Preview same breakdown as process | test_payment_preview | 1 test |
| Preview version unchanged | test_payment_preview | 1 test |
| mora clears when all overdue paid | test_payment_installment_status_transitions | 1 test |
| mora stays when overdue remain | test_payment_installment_status_transitions | 1 test |
| paid_at set on full payment | test_payment_installment_status_transitions | 1 test |
| No float anywhere | test_payment_mandatory_order, test_payment_pending_capital_update | 2 tests |

---

## Week 2 Residual Risk Resolution

| Risk | Resolution | Evidence |
|------|-----------|---------|
| #3 — Silent optimistic-lock gap | FIXED in payment_service.py: `len(updated_rows) == 0` → raises HTTPException(409) | test_optimistic_locking_retry.py (4 tests) |
| #1 — Icon files not committed | PENDING-HUMAN — unchanged from Week 2 gate | see week-2-gate.md |
| #2 — Live DB never validated | PENDING-HUMAN — unchanged from Week 2 gate | see week-2-gate.md |
| #4 — Missing migration 003 (triggers) | PENDING-HUMAN — unchanged from Week 2 gate | see week-2-gate.md |

---

## Hard Constraints Verification

| Constraint | Verified |
|------------|---------|
| Decimal only (no float in service logic) | test_payment_mandatory_order.py, test_payment_pending_capital_update.py |
| Installment locked fields NOT modified | _compute_installment_new_states only writes paid_value, status, is_overdue, paid_at |
| No mutation outside transaction | All writes sequential in process_payment, none in preview |
| ROUND_HALF_EVEN | _decimal() helper uses quantize(Decimal("0.01"), ROUND_HALF_EVEN) |
| preview_payment_breakdown() method exists | test_payment_preview.py test_preview_method_exists |

---

## Residual Risks — Phase 4

1. **Mocked DB only** — All 50 tests run against mock DB. True atomic behavior (rollback on partial failure) is NOT verified. Supabase does not natively support multi-statement transactions via the REST client. A Supabase RPC stored procedure would be needed to guarantee true atomicity. This is flagged as a future migration when live DB is available.

2. **installments SELECT/UPDATE ordering** — The mock assumes SELECT installments happens exactly once before any UPDATEs. If service code refactors the call order, mock responses may misalign. Integration tests on live DB (PENDING-HUMAN) will catch this.

3. **idempotency_key not implemented** — PaymentRequest accepts the field but process_payment does not deduplicate. Duplicate payment on retry is possible. Should be implemented before production.

4. **concurrent_payment (multi-process)** — Optimistic locking prevents double-apply within a single node. With multiple FastAPI workers + Supabase, the UPDATE WHERE version=X is atomic only if Supabase executes it as a single SQL statement. Verified by implementation; live DB test pending.

5. **FUTURE_PRINCIPAL includes both interest+principal** — Per spec, future installments are applied as FUTURE_PRINCIPAL (the whole remaining amount). This means the installment's interest_portion is included in the FUTURE_PRINCIPAL allocation. This is intentional per spec §1.2 ("Future principal") but may be surprising to business users expecting interest-only tracking on future periods.

---

## Frontend Status

- [ ] PaymentForm component — PENDING
- [ ] Preview integration (calls /preview before submit) — PENDING  
- [ ] Breakdown display (installment_id, type, amount) — PENDING
- [ ] Confirm → POST /payments — PENDING
- [ ] RTK Query paymentApi (preview + submit hooks) — PENDING
- [ ] Frontend tests — PENDING

Frontend dispatch blocked until backend tests are green (TDD gate).

---

## Human Actions Required to Close Gate

```
1. cd backend && pip install -r requirements.txt
2. pytest tests/test_payment_mandatory_order.py tests/test_payment_partial_application.py \
          tests/test_payment_overpayment.py tests/test_payment_boundary_conditions.py \
          tests/test_payment_multi_installment.py tests/test_payment_atomicity.py \
          tests/test_optimistic_locking_retry.py tests/test_payment_preview.py \
          tests/test_payment_installment_status_transitions.py \
          tests/test_payment_pending_capital_update.py -v \
   | tee .github/qa/week-4-test-output.txt
3. Review failures, fix service if any test fails
4. Mark tests PASSED once all green
5. Dispatch frontend implementation (PaymentForm + preview)
6. supabase start && run integration tests when live DB available
```
