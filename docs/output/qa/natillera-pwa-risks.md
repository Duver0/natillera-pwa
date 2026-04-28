# Natillera PWA — Risk Matrix (ASD Classification)
# SPEC-001 v2.2 | QA Lead | 2026-04-27

---

## Classification Scale

| Level | Definition | Gate Impact |
|-------|-----------|-------------|
| **ALTO** | Financial correctness, data integrity, security. Defect → client dispute or data loss. | BLOCKER — cannot ship |
| **MEDIO** | Functional correctness degraded under specific conditions. Detected by QA gate. | QA GATE — must fix before IMPLEMENTED |
| **BAJO** | UX/performance degradation. No financial or data integrity impact. | Nice-to-have, deferred acceptable |

---

## ALTO — Critical, Blocker

### RISK-001 | Interest Formula Error → Client Disputes
- **Description**: Wrong computation of `interest = pending_capital * (annual_rate/100) / periods_per_year` produces incorrect installment charges. Any float vs Decimal inconsistency or wrong `periods_per_year` constant propagates silently.
- **Impact**: Client overcharged or undercharged. Financial dispute. Business liability.
- **Likelihood**: Medium — formula is simple but rounding and float conversion are observed anti-patterns in similar codebases.
- **Current State**: Unit tested in `test_installment_locked_values.py` (12 tests). Formula validated for MONTHLY. WEEKLY, BIWEEKLY, DAILY need explicit test coverage.
- **Mitigation**:
  - Unit test: verify exact Decimal output for all 4 periodicities against spec examples.
  - Gherkin acceptance: INT-01 through INT-04.
  - Code: `Decimal + ROUND_HALF_EVEN` enforced in `payment_service.py` — must be verified in `installment_service.py` as well (currently uses `round()` on float).
- **Residual Gap**: `installment_service.py` uses `round(10000.0 / 12, 2)` (float arithmetic) — not Decimal. ALTO risk until corrected and retested.

---

### RISK-002 | Payment Order Not Applied → Debt Miscalculation
- **Description**: If the 3-pool mandatory order (overdue interest → overdue principal → future principal) is bypassed or misimplemented, clients can reduce principal without clearing interest, causing permanent debt miscalculation.
- **Impact**: Incorrect pending_capital. Client ledger inaccurate. Audit trail misleads.
- **Likelihood**: Medium — complex multi-installment FIFO logic; the preview path (`_compute_breakdown_3pool`) is Python but the atomic path delegates to a SQL RPC (`process_payment_atomic`). A mismatch between the two is a live risk.
- **Current State**: 6 tests in `test_payment_mandatory_order.py`, mocked DB. SQL RPC not directly tested in current suite.
- **Mitigation**:
  - Atomic RPC integration test: create real credit → real overdue installment → call `process_payment` → verify DB state.
  - Preview vs. actual parity test: same inputs, both must return identical breakdown.
  - Gherkin: PAY-01, PAY-02, PAY-03.

---

### RISK-003 | Mora Stale → UI Shows False Positive / False Negative
- **Description**: If mora is not recalculated on every `GET /credits/{id}`, a client may show mora=false while overdue installments exist (or vice versa). Mora drives UI alerts, payment flow eligibility, and installment generation.
- **Impact**: Wrong mora display → incorrect payment guidance → client dispute.
- **Likelihood**: Medium — recalculation-on-read is implemented in `get_credit()` pseudocode in spec; actual implementation in `credit_service.py` is unverified (Phase 2 tasks still open per task list).
- **Current State**: No test file for `test_mora_detection.py` or `test_mora_fresh_on_read.py` found — both listed as TODO in spec §3.1.
- **Mitigation**:
  - Implement and pass `test_mora_detection.py` and `test_mora_fresh_on_read.py`.
  - Gherkin: MORA-01 through MORA-04.
  - Integration test: advance date past expected_date without payment → GET credit → assert mora=true.

---

### RISK-004 | Cascade Delete Fails → Orphaned Records
- **Description**: If FK `ON DELETE CASCADE` is not applied or migration is incomplete, deleting a client leaves orphaned credits, installments, savings, and payments in the DB. These orphans corrupt aggregations and may be exposed via other users.
- **Impact**: Data integrity violation. Orphaned financial records. Potential privacy leak.
- **Likelihood**: Low — schema DDL has CASCADE defined. Risk is in migration not being run or Supabase RLS blocking the cascade.
- **Current State**: Supabase schema migration status = pending (Phase 6 task open). No integration test for cascade delete found.
- **Mitigation**:
  - Run and verify migration in staging Supabase project.
  - Integration test: create client with credits + savings → delete → assert all child tables empty.
  - Gherkin: DEL-01, DEL-02.

---

## MEDIO — Important, QA Gate

### RISK-005 | Decimal Rounding → $0.01 Mismatch
- **Description**: Inconsistent rounding between Python (`round()` on float) and Decimal quantize can produce 1-cent discrepancies in installment values, payment breakdowns, or savings liquidation results.
- **Impact**: Ledger mismatch. Client sees different total than system records.
- **Likelihood**: High probability in `installment_service.py` (confirmed float usage in test helpers and spec pseudocode). Lower in `payment_service.py` (Decimal enforced).
- **Current State**: `payment_service.py` uses `ROUND_HALF_EVEN` correctly. `installment_service.py` test helper uses `round(float, 2)` — acceptable in tests but service implementation must also use Decimal.
- **Mitigation**:
  - Audit `installment_service.py` for float arithmetic — replace with `Decimal.quantize(Decimal("0.01"), ROUND_HALF_EVEN)`.
  - Add boundary test: $10 000 / 12 = $833.33 (not $833.3333...).
  - Savings formula test: 1500 * 10 / 100 = 150.00 exactly.

---

### RISK-006 | Concurrent Payment Race → Lost Update
- **Description**: Two simultaneous payments on the same credit without proper optimistic locking result in one payment overwriting the other, corrupting `pending_capital` and `version`.
- **Impact**: Lost payment record or double-application. Audit trail incomplete.
- **Likelihood**: Low in single-user MVP. Medium in multi-user (SPEC-002).
- **Current State**: `VersionConflict` exception implemented in `payment_service.py`. 4 tests in `test_optimistic_locking_retry.py` pass with mocked DB. SQL RPC enforces lock at DB level (CF-2 resolved per service comments).
- **Mitigation**:
  - Integration test with concurrent async requests to same credit.
  - Verify SQL RPC raises SQLSTATE P0001 on version mismatch.
  - Frontend handles 409 and prompts retry (tested in `PaymentForm.test.tsx`).
  - Gherkin: LOCK-OPT-01, LOCK-OPT-02.

---

### RISK-007 | Token Expiry Mid-Payment → Session Timeout
- **Description**: Firebase/Supabase JWT expires between the preview call and the confirm payment submit. The confirm call returns 401, payment is not recorded, but the user may believe it was.
- **Impact**: User confusion. No data corruption, but operational trust impact.
- **Likelihood**: Low — payment preview + confirm cycle is typically under 60 seconds. JWT TTL is 1 hour.
- **Current State**: No auto-refresh logic confirmed in frontend (auth middleware verified as implemented, but refresh not specified).
- **Mitigation**:
  - Implement token auto-refresh in API layer (RTK Query `baseQuery` with re-auth).
  - Show clear error message on 401 during payment: "Session expired. Please log in again."
  - Do not auto-submit after refresh (security).

---

## BAJO — Nice-to-Have

### RISK-008 | Large List Render Slow
- **Description**: Rendering 1000+ clients or 100+ installments in a list without pagination causes slow initial render and potential scroll jank.
- **Impact**: UX degradation. No financial or data impact.
- **Likelihood**: Low for MVP user volume.
- **Current State**: Pagination and DB indexes defined in schema. Frontend pagination not yet implemented (Phase 7 open).
- **Mitigation**:
  - Backend: `GET /clients` already has indexes on `phone` and `deleted_at`. Add `LIMIT`/`OFFSET` to all list endpoints.
  - Frontend: virtual scroll or paginated component when list > 50 items.
  - Performance SLA: GET /clients (1000 records) < 500ms.

---

## Risk Summary

| ID | Risk | Level | Gate | Status |
|----|------|-------|------|--------|
| RISK-001 | Interest formula error | ALTO | BLOCKER | Partial — float in installment_service |
| RISK-002 | Payment order not applied | ALTO | BLOCKER | Partial — mocked tests only, no integration |
| RISK-003 | Mora stale on read | ALTO | BLOCKER | Open — test files missing |
| RISK-004 | Cascade delete fails | ALTO | BLOCKER | Open — migration pending, no integration test |
| RISK-005 | Decimal rounding mismatch | MEDIO | QA GATE | Partial — payment OK, installment TBD |
| RISK-006 | Concurrent payment race | MEDIO | QA GATE | Partial — mocked only, no integration |
| RISK-007 | Token expiry mid-payment | MEDIO | QA GATE | Open — no auto-refresh confirmed |
| RISK-008 | Large list render slow | BAJO | Deferred | Indexes exist, pagination not implemented |
