# Phase 4 Payment Processing — Adversarial Audit
Date: 2026-04-24
Auditor: orchestrator (senior financial-systems audit mode)
Scope: payment_service.py, payment_router.py, repositories, tests, migrations

---

## ❌ Critical Failures

### CF-1: No Real Atomicity — Supabase REST Calls Are Independent, No Rollback
**File:** `backend/app/services/payment_service.py:179–215`
**Severity:** Critical — data corruption on partial failure is REAL and unremediated.

The comment at line 179 literally reads: `# Persist installment updates (individual updates — Supabase mock-compatible)`. This is an admission, not a fix. The service issues:
1. N individual `UPDATE installments` REST calls in a loop (lines 181–187)
2. One `UPDATE credits` REST call (lines 203–215)
3. One `INSERT payments` REST call (line 243)
4. One `INSERT financial_history` REST call (lines 247–260)

These are four independent HTTP requests to Supabase PostgREST. If step 1 partially completes (e.g., 2 of 3 installments updated) and step 2 fails, the database is left in a permanently inconsistent state: installment paid_values are updated but pending_capital is not reduced, and no payment record exists. There is no compensating rollback, no retry covering the already-applied installment updates, and no DB-side transaction.

The contract at `.github/specs/payment-contract.md:253` explicitly requires: "All writes inside a single atomic transaction (Supabase RPC or explicit transaction)." This requirement is violated. No RPC call is made. No `BEGIN`/`COMMIT` transaction is used. The code uses the Supabase JS-style chained mock interface which has no transaction support.

### CF-2: Installment Writes BEFORE Optimistic Lock Check — Incorrect Operation Order
**File:** `backend/app/services/payment_service.py:181–215`

The service updates installments (lines 181–187) BEFORE the optimistic lock UPDATE on credits (lines 203–215). This means:
- On a version conflict (another concurrent payment), installments are already dirtied before the 409 is raised.
- The conflict raises an `HTTPException(409)` at line 219, but the installment updates at lines 181–187 have already committed to the database.
- The caller gets a 409 and retries, but the installments now have stale `paid_value` increments from the failed attempt. The retry will double-apply payment to those installments.

The canonical algorithm in the contract (`.github/specs/payment-contract.md:158–164`) specifies: installment state updates, credit UPDATE, INSERT payment — all inside one transaction. Separating them and doing installment updates first destroys the invariant.

### CF-3: `_compute_breakdown` Allocates FUTURE_PRINCIPAL While Overdue Exists — Possible Order Violation
**File:** `backend/app/services/payment_service.py:53–116`

The loop iterates installments ordered by `expected_date ASC`. This is FIFO across ALL installments, mixing overdue and future. The overdue check at line 67 is per-installment (`is_overdue = expected_date < today`), so the loop correctly applies overdue logic per installment in order. However:

The business rule is: ALL overdue interest across ALL overdue installments must be cleared BEFORE any overdue principal, and ALL overdue principal across ALL overdue installments must be cleared BEFORE any future principal. The current loop does NOT implement this — it processes one installment at a time, handling both interest and principal for each installment before moving to the next.

**Example:** Two overdue installments: InstA (interest=100, principal=500), InstB (interest=50, principal=300). Payment = 130.
- Current code: InstA gets 100 (interest) + 30 (principal). InstB gets 0. Total: 30 principal applied from InstA.
- Correct spec behavior (per §US-005 "Apply in STRICT order: 1. ALL overdue interest, 2. ALL overdue principal, 3. Future"): 130 should go: 100 (InstA interest) + 30 (InstB interest). Zero principal touched.

The current algorithm does not aggregate ALL overdue interest first. It interleaves interest+principal per installment. This is a direct violation of Business Rule #1 (payment mandatory order) and §US-005.

### CF-4: `mora_since` Never SET on Mora Activation — Only Preserved If Already Set
**File:** `backend/app/services/payment_service.py:208`

Line 208:
```python
"mora_since": None if not mora_after else credit.get("mora_since"),
```

If `mora_after` is True AND `credit["mora_since"]` is already `None` (e.g., first time mora is detected via payment), `mora_since` stays `None`. The spec (§US-006, §1.2) requires `mora_since` = earliest overdue installment date when mora=true. The service never queries for the earliest overdue installment date to populate `mora_since`. It only preserves the existing value, which is `None` when mora first triggers.

### CF-5: `idempotency_key` Accepted in Schema But Completely Ignored in Logic
**File:** `backend/app/models/payment_model.py:18`, `backend/app/services/payment_service.py` (entire file)

`PaymentRequest.idempotency_key` is declared at model line 18. The contract explicitly states (`.github/specs/payment-contract.md:40`): "If provided and already used, returns original response (no duplicate write)." The service at `payment_service.py` never references `body.idempotency_key`. There is no lookup, no uniqueness check, no deduplication. On a network retry after a successful payment (common in 409 retry scenarios), a duplicate payment will be double-applied. This is a critical financial correctness failure — the mechanism designed to prevent exactly this class of double-apply is present in the schema and contract but dead in the implementation.

---

## ⚠️ High Risk Issues

### HR-1: Optimistic Lock Detected by `len(dict)` Not `len(list)` — Broken Conflict Detection
**File:** `backend/app/services/payment_service.py:216–222`, `backend/tests/conftest_payment.py:133`

The service checks `len(updated_rows) == 0` at line 217 where `updated_rows = update_result.data or []`. When Supabase PostgREST returns a successful row update, `data` is a list of updated records. But `conftest_payment.py` line 133 returns `MagicMock(data=credit)` — a dict, not a list — as the execute result for the credits SELECT. More critically, line 168 correctly returns `MagicMock(data=[credit])` for the UPDATE chain.

The problem: the mock conflates SELECT and UPDATE responses in the simplified `_build_db_mock` in `test_payment_service.py:197` — it returns `MagicMock(data=credit)` (a dict) for ALL credits table calls including UPDATE. `len(dict)` = number of keys (e.g., 7), never 0. The optimistic lock conflict detection test at `test_payment_service.py` would ALWAYS see a non-zero length even on a version conflict, because the mock returns a dict. The four tests in `test_payment_service.py` use `_build_db_mock` (line 166), not `build_db_mock` from conftest. This means test_payment_service.py's optimistic lock detection is never actually exercised — the mock is wrong.

### HR-2: `process_payment` Queries `UPCOMING` + `PARTIALLY_PAID` But Ignores `OVERDUE` Status Installments
**File:** `backend/app/services/payment_service.py:149–156`

The installments query filters `status IN ['UPCOMING', 'PARTIALLY_PAID']`. An installment in `OVERDUE` status (if the schema ever sets it — the schema uses `UPCOMING`, `PARTIALLY_PAID`, `PAID`, `SUSPENDED` per migration line 93) would be excluded. This is actually consistent with the schema which has no `OVERDUE` status. However: the overdue detection at line 67 relies on `expected_date < today AND status != PAID`. A `PARTIALLY_PAID` installment past its date is correctly caught. But a `SUSPENDED` installment past its date would be silently skipped and never appear in the payment allocation, even if it has unpaid balance. No guard exists.

### HR-3: Overpayment Reduces `pending_capital` Without Reducing Installment `paid_value`
**File:** `backend/app/services/payment_service.py:172–174`

After `_compute_breakdown` exhausts all installments, if `remaining_after > 0`, lines 172–174 reduce `new_pending_capital` directly:
```python
if remaining_after > Decimal("0.00") and new_pending_capital > Decimal("0.00"):
    excess_to_capital = min(remaining_after, new_pending_capital)
    new_pending_capital = max(Decimal("0.00"), new_pending_capital - excess_to_capital)
```
No installment is updated. No `applied_to` entry is created for this excess. The payment record's `applied_to` array will omit this capital reduction. The audit trail is incomplete — a capital reduction occurs that has no corresponding installment entry and is not reflected in `applied_to`. This excess also adds to `total_principal_applied` implicitly (by reducing `new_pending_capital`), but the `applied_to` field does not record it. The contract response shape has no field for this "raw capital reduction" scenario.

### HR-4: Auto-Close Logic Ignores Unpaid Installments
**File:** `backend/app/services/payment_service.py:177`

Line 177: `new_credit_status = "CLOSED" if new_pending_capital <= Decimal("0.00") else credit["status"]`

The spec (§1.3 #1) states: "Auto-close when pending_capital = 0 AND all installments paid." The code closes on `pending_capital = 0` alone, ignoring whether all installments are PAID. An overpayment that drives pending_capital to 0 while installments remain PARTIALLY_PAID would auto-close the credit while installments still show outstanding balances.

### HR-5: `pending_capital` Stored as String in DB, Loaded as String, No Type Guard
**File:** `backend/app/services/payment_service.py:167`, `backend/tests/test_payment_service.py:20`

`conftest_payment.py:38` stores `pending_capital` as `str(pending)`. The service reads it at line 167: `pending_capital = _decimal(credit["pending_capital"])` — this correctly calls `_decimal()` which does `Decimal(str(value))`. That path is safe.

However, `test_payment_service.py:20` uses `make_credit` which stores `float(pending)` — a float in the mock data. So `_decimal(float_value)` is called with a float in test scenarios. `Decimal(str(float(Decimal("100"))))` = `Decimal("100.0")` which rounds correctly. But `Decimal(str(float(0.1)))` = `Decimal("0.1")` due to Python's `str(float)` repr. This is a latent precision gap in tests, not a confirmed runtime bug, but shows the test helpers use float internally while claiming "Decimal everywhere."

### HR-6: `VersionConflict` Exception Class Defined But Never Raised by `process_payment`
**File:** `backend/app/services/payment_service.py:29`, `backend/app/services/payment_service.py:218–222`, `backend/app/routes/payment_router.py:49`

`VersionConflict` is defined at line 29. The router catches it at `payment_router.py:49`. But `process_payment` never raises `VersionConflict` — it raises `HTTPException(status_code=409)` directly at line 219. The `except VersionConflict` in the router (line 49) is dead code. This creates a semantic disconnect: the router's exception handling contract is broken, and if the raise is ever refactored to actually raise `VersionConflict`, the test `test_version_conflict_exception_type_is_version_conflict` accepts HTTPException with status_code=409 as valid — so the tests would pass either way, masking the dead catch.

---

## 🟡 Design Weaknesses

### DW-1: Contract Requires Canonical Algorithm But Implementation Deviates Without Flag
**File:** `payment-contract.md:142`, `payment_service.py:86–99`

The canonical algorithm in the contract at line 142 computes `principal_remaining = installment.principal_portion - amount_already_applied_to_principal`. The code at lines 89–90 computes it as `inst_expected - inst_paid` after interest deduction. For a fully interest-paid installment this is mathematically equivalent. But if `inst_paid` includes partial principal from a previous payment, the calculation diverges from the contract definition. The contract says to track `amount_already_applied_to_principal` as a separate concept from total paid; the code uses `inst_expected - inst_paid` as a proxy. This is fragile and not documented as an intentional deviation.

### DW-2: `_compute_installment_new_states` is a Separate Post-Pass — State Drift Risk
**File:** `backend/app/services/payment_service.py:401–446`

`_compute_installment_new_states` recomputes installment state from `applied_entries` in a second pass. If `_compute_breakdown` is modified and `applied_entries` does not capture all mutations (e.g., the excess capital path adds no entry), the second pass will miss installments. The two-pass design creates a surface where the computation in pass 1 and the state written in pass 2 can diverge. A single-pass design would be safer.

### DW-3: `today = date.today()` Called Mid-Request — Clock Skew Risk
**File:** `backend/app/services/payment_service.py:158`, `backend/app/services/payment_service.py:193`

`today` is set at line 158. A second implicit `today` comparison is done at line 196 (`.lt("expected_date", today.isoformat())`). Between these two calls the day can tick over midnight. In a financial system processing payments near midnight, an installment classified as "future" in the breakdown could be classified as "overdue" in the mora recheck (or vice versa), producing inconsistent state in a single payment.

### DW-4: No Database-Level Constraint Preventing Locked Field Mutation
**File:** `database/migrations/001_initial_schema.sql:82–97`

The schema has no trigger or generated column preventing writes to `expected_value`, `principal_portion`, `interest_portion`, or `expected_date` on installments after creation. The spec (§1.2 "Installments Fixed") declares these immutable, but the guarantee relies entirely on application code. An application bug, direct DB access, or future developer mistake can corrupt these fields with no DB-level rejection.

### DW-5: `financial_history` ON DELETE CASCADE Will Destroy Audit Trail
**File:** `database/migrations/001_initial_schema.sql:186`

`financial_history.client_id` references `clients(id) ON DELETE CASCADE`. The spec (§US-001 "cascade-delete") says "archive history records (immutable audit trail)." Deleting a client cascades and deletes all `financial_history` rows for that client, destroying the audit trail. This directly contradicts "immutable audit log." The FK should be `ON DELETE SET NULL` or `ON DELETE RESTRICT`.

### DW-6: `payment_date` Defaults to Server Date But Allows Past/Future Dates Without Validation
**File:** `backend/app/services/payment_service.py:225`

`payment_date = (body.payment_date or today).isoformat()` — a caller can supply any past or future date with no validation. This allows backdating payments arbitrarily, corrupting the financial history timeline. The model (`payment_model.py:21`) makes it `Optional[date]` with no bounds.

---

## 🧪 Test Gaps

**TG-1: `test_payment_service.py` — Payment Order Across Multiple Overdue Installments**
Missing test: 2+ overdue installments, payment covers all interest of both before touching any principal. Current tests use a single installment. The multi-installment order violation (CF-3) is completely untested.

**TG-2: No Test for `idempotency_key` Duplicate Detection**
The feature is in the schema and contract. Zero test coverage. A duplicate retry with the same key should return the original response, not create a second payment.

**TG-3: `test_payment_atomicity.py` Does Not Verify Rollback — Only That Exception Bubbles**
`test_atomicity_failure_mid_installment_update_raises` (line 19) asserts only `pytest.raises(Exception)`. It does NOT assert that the first installment's update was reversed. With real Supabase (no transaction), the first write is permanent. The test masks the real failure mode.

**TG-4: `test_atomicity_credit_not_updated_on_service_failure` — No Assertion Made**
Lines 141–148 in `test_payment_atomicity.py`: the test has a comment describing what should be checked, but there is NO `assert` statement verifying that payments were not inserted. The test body ends with a comment. This test provides ZERO coverage.

**TG-5: No Test for `mora_since` Set on First Mora Detection**
After a payment that leaves overdue installments, `mora_since` should be set to the earliest overdue date. No test verifies this. CF-4 is completely uncovered.

**TG-6: No Test for Overpayment Driving `pending_capital` to Zero → Credit CLOSED**
No test verifies the auto-close path triggers, the credit status changes to CLOSED, and the state is correct.

**TG-7: No Test for Payment on CLOSED or SUSPENDED Credit**
The check at `payment_service.py:144` rejects non-ACTIVE credits, but there is no test confirming this returns 400 for CLOSED or SUSPENDED status.

**TG-8: No Test for Zero-Remainder Mid-Iteration (Exact Match)**
No test covers the case where `remaining` hits exactly 0 after filling an installment, verifying the loop breaks and no future installment is touched.

**TG-9: No Boundary Test — `remaining == installment.remaining` Exact Match Both Sides**
Off-by-one on the `<=` comparison in `_compute_breakdown` line 63 (`remaining_owed <= 0`) is untested at the exact boundary on both sides (exact match and 1-cent under).

**TG-10: No Decimal Drift / Precision Accumulation Test**
No test runs 100+ payments of 0.01 and verifies accumulated `paid_value` and `pending_capital` match expected totals. ROUND_HALF_EVEN behavior on boundary amounts is untested.

**TG-11: No Concurrent Payment Race Condition Test**
Two simultaneous `process_payment` calls on the same credit. Neither a unit test nor integration test simulates this. The optimistic lock is the only defense; its real behavior under concurrency is untested.

**TG-12: `test_optimistic_locking_retry.py` — Retry Logic Tested? No. Only 409 Response.**
The tests verify a conflict raises an exception. No test verifies that the client-side retry succeeds on the second attempt, or that after conflict the database is in a consistent (unmodified) state. More critically: the service itself has no retry logic — it raises 409 and expects the caller to retry. This is documented in the router comment but never tested end-to-end.

**TG-13: No Test for Payment Amount = 0 or Negative (Pydantic Boundary)**
`PaymentRequest.amount` has `gt=0` validator. No test verifies this rejects 0, negative, or None, and returns 422.

**TG-14: No Test for Credit With Zero Installments**
Payment on a credit that has no installments at all — `applied_entries` will be empty, `total_principal_applied` = 0, `remaining_after` = full amount. Overpayment path triggers. Behavior untested.

**TG-15: No Test Verifying `operator_id` Is Stored Correctly**
`operator_id` validation (non-empty enforced by Pydantic) is not tested. No test verifies it is persisted in the payment record.

---

## ✅ What Is Actually Solid

**S-1: Decimal Usage in Service Core**
`payment_service.py:33–36` — `_decimal()` correctly uses `Decimal(str(value))` to avoid float coercion before quantization, with explicit `ROUND_HALF_EVEN`. Every monetary operation in `_compute_breakdown` uses `_decimal()` consistently. No raw float arithmetic present.

**S-2: Optimistic Lock WHERE Clause Is Correct**
`payment_service.py:212–213` — The UPDATE predicate `.eq("version", credit["version"])` is included alongside the ID filter. The version is incremented by exactly 1 (`new_version = credit["version"] + 1`, line 199). The 0-row detection at line 217 correctly raises a 409. The mechanism is architecturally correct even though the test mocks for it are broken (HR-1).

**S-3: Locked Installment Fields Never Written by `_compute_installment_new_states`**
`payment_service.py:439–444` — The update payload contains only `paid_value`, `status`, `paid_at`, `is_overdue`. Fields `expected_value`, `principal_portion`, `interest_portion`, `expected_date` are never included. This correctly honors the immutability contract.

**S-4: `conftest_payment.py` Fixture Design (SELECT vs UPDATE Routing)**
`conftest_payment.py:155–245` — The `build_db_mock` fixture correctly separates SELECT and UPDATE chains for both credits and installments, tracks call counts to differentiate first vs second installments SELECT, and returns appropriate data shapes. This is significantly better than the naive `_build_db_mock` in `test_payment_service.py`.

**S-5: Schema Locks `principal_portion > 0` and `expected_value > 0`**
`001_initial_schema.sql:89–90` — DB constraints reject zero or negative locked values at the schema level, providing a partial backstop for installment data integrity.

---

## 🔧 Required Fixes (Prioritized)

**P0-1: Implement Real DB Transaction for All Payment Writes**
File: `payment_service.py:179–260`
Use Supabase RPC (PostgreSQL stored procedure) or Supabase's `BEGIN`/`COMMIT` via raw SQL to wrap all writes (installment UPDATEs + credit UPDATE + payments INSERT + financial_history INSERT) in a single atomic transaction. The current "Supabase mock-compatible" comment is not an acceptable production excuse. Expected behavior: either all writes commit or none do.

**P0-2: Reorder Operations — Optimistic Lock BEFORE Installment Writes**
File: `payment_service.py:181–215`
Perform the `UPDATE credits WHERE version=X` FIRST. Only if that succeeds (1 row updated), proceed with installment updates and payment insert — ideally all inside the same transaction (P0-1). Expected behavior: a version conflict causes zero DB mutations.

**P0-3: Fix Mandatory Payment Order — Aggregate ALL Overdue Interest Before ANY Overdue Principal**
File: `payment_service.py:39–116`
Refactor `_compute_breakdown` to first sweep all installments collecting total overdue interest owed, apply payment to that pool, then sweep for overdue principal, then future principal. The current per-installment FIFO loop violates Business Rule #1.

**P0-4: Implement `idempotency_key` Deduplication**
File: `payment_service.py:121–273`, `payment_model.py:18`
Before processing, if `body.idempotency_key` is provided, query payments table for a record with matching `idempotency_key`. If found, return the original response. The `payments` table needs an `idempotency_key UUID UNIQUE` column. Expected behavior: duplicate retry with same key returns original payment response, zero additional writes.

**P1-1: Fix `mora_since` to Set Earliest Overdue Date on Mora Activation**
File: `payment_service.py:193–208`
After the post-payment overdue query, if `mora_after` is True and `credit["mora_since"]` is None, query for the minimum `expected_date` among remaining overdue installments and use that as `mora_since`. Expected behavior: `mora_since` correctly populated on first mora detection.

**P1-2: Fix Auto-Close to Require All Installments PAID**
File: `payment_service.py:177`
Change to: `new_credit_status = "CLOSED" if new_pending_capital <= 0 and all installments cleared else credit["status"]`. Query installment count remaining unpaid before setting CLOSED.

**P1-3: Fix `financial_history` FK to Preserve Audit Trail on Client Delete**
File: `database/migrations/001_initial_schema.sql:186`
Change `ON DELETE CASCADE` to `ON DELETE SET NULL` on `financial_history.client_id`. Add a corresponding migration. Expected behavior: deleting a client preserves all financial history rows with `client_id = NULL`.

**P1-4: Fix `test_atomicity_credit_not_updated_on_service_failure` — Add Assertions**
File: `backend/tests/test_payment_atomicity.py:141–148`
The test has no assert. Add: `assert payment_insert_called["called"] is False`. Without this the test is vacuously passing.

**P2-1: Add DB Trigger to Prevent Locked Field Mutation on Installments**
File: `database/migrations/001_initial_schema.sql` (new migration)
Add a `BEFORE UPDATE` trigger on `installments` that raises an exception if any of `expected_value`, `principal_portion`, `interest_portion`, `expected_date` are changed. Expected behavior: application bugs trying to modify locked fields are rejected at DB level.

**P2-2: Validate `payment_date` — Reject Future Dates**
File: `payment_model.py:21`, `payment_service.py:225`
Add a Pydantic validator: `payment_date` must be <= today if provided. Prevents arbitrary backdating.

**P2-3: Fix `test_payment_service.py` `_build_db_mock` — Returns Dict Not List for Credit UPDATE**
File: `backend/tests/test_payment_service.py:197`
The mock returns `MagicMock(data=credit)` (dict) for all credits calls. The optimistic lock check does `len(data or [])` — on a dict, len = key count, never 0. Replace with `MagicMock(data=[credit])` for the UPDATE path so version conflict detection is actually exercised.
