# E2E Validation Checklist — Natillera PWA
# Version: 1.0 | Date: 2026-04-23 | Based on SPEC-001 v2.0 + SPEC-002 v1.0

---

## PRECONDITIONS

- FastAPI running at `http://localhost:8000`
- Supabase PostgreSQL accessible (env vars: `SUPABASE_URL`, `SUPABASE_KEY`, `DATABASE_URL`)
- `SAVINGS_RATE` env var set (e.g., `10` for 10%)
- Two isolated test users pre-registered (USER_A, USER_B) for cross-user tests
- `psql` connected to Supabase DB: `psql $DATABASE_URL`
- Time-travel requires `pg_catalog.set_config` or `CURRENT_DATE` override (see Step 6)

---

## SECTION 1 — EXECUTABLE E2E CHECKLIST

### Step 1: Register + Login

| # | Action | Expected | Pass | Fail | Notes |
|---|--------|----------|------|------|-------|
| 1.1 | POST `/auth/register` with `{email, password (>=8 chars, 1 uppercase, 1 number)}` | 201 — user created, session token returned | | | |
| 1.2 | Check UI: redirect to dashboard, no error banner | Dashboard visible | | | |
| 1.3 | POST `/auth/login` with same credentials | 200 — `access_token` + `refresh_token` in response | | | |
| 1.4 | Store `access_token` in browser localStorage / sessionStorage | Token persists on refresh | | | |
| 1.5 | Wait for token near-expiry or force expiry; make authenticated request | Auto-refresh returns new `access_token` without re-login | | | |
| 1.6 | POST `/auth/register` with same email again | 400/409 — `email_already_registered` | | | |
| 1.7 | POST `/auth/register` with password `abc` (< 8 chars) | 422 — validation error | | | |

**DB Query — Step 1:**
```sql
-- Verify user created in Supabase auth.users
SELECT id, email, created_at, email_confirmed_at
FROM auth.users
WHERE email = '<test_email>';

-- Verify no duplicate email
SELECT COUNT(*) FROM auth.users WHERE email = '<test_email>';
-- Expected: 1
```

---

### Step 2: Create Client

| # | Action | Expected | Pass | Fail | Notes |
|---|--------|----------|------|------|-------|
| 2.1 | POST `/clients` with `{first_name, last_name, phone}` using Bearer token | 201 — client object with `id`, `created_at` | | | |
| 2.2 | UI: client appears in list with name, phone | Client row visible | | | |
| 2.3 | Verify `user_id` on client record matches authenticated user | Row-level isolation confirmed | | | |
| 2.4 | POST `/clients` with same `phone` again | 409/400 — phone unique constraint | | | |
| 2.5 | POST `/clients` without `phone` field | 422 — required field error | | | |
| 2.6 | As USER_B, GET `/clients` — must NOT see USER_A clients | 200 with empty list or only USER_B's clients | | | |

**DB Query — Step 2:**
```sql
-- Verify client persisted with correct owner
SELECT id, first_name, last_name, phone, user_id, created_at, deleted_at
FROM clients
WHERE phone = '<test_phone>';
-- Expected: 1 row, deleted_at = NULL, user_id = '<expected_user_uuid>'

-- Verify RLS: client not visible to other user
-- Run as USER_B's DB session (set role via Supabase RLS):
SET LOCAL "request.jwt.claim.sub" = '<user_b_uuid>';
SELECT COUNT(*) FROM clients WHERE user_id = '<user_a_uuid>';
-- Expected: 0
```

---

### Step 3: Create Credit

| # | Action | Expected | Pass | Fail | Notes |
|---|--------|----------|------|------|-------|
| 3.1 | POST `/clients/<client_id>/credits` with `{initial_capital: 1000.00, periodicity: "MONTHLY", annual_interest_rate: 24.00, start_date: "<today>"}` | 201 — credit with `pending_capital = 1000.00`, `version = 1`, `mora = false`, `status = ACTIVE` | | | |
| 3.2 | UI: credit appears in client detail with pending capital, next period date | Correct display | | | |
| 3.3 | `next_period_date` = `start_date + 1 month` | Date correct | | | |
| 3.4 | `mora_since` = null | No mora at creation | | | |
| 3.5 | POST credit with `initial_capital = 0` | 422 — must be > 0 | | | |
| 3.6 | POST credit with `initial_capital = -500` | 422 — must be > 0 | | | |

**DB Query — Step 3:**
```sql
SELECT id, client_id, initial_capital, pending_capital, version, periodicity,
       annual_interest_rate, status, start_date, next_period_date, mora, mora_since
FROM credits
WHERE client_id = '<client_id>'
ORDER BY created_at DESC LIMIT 1;
-- Expected: pending_capital = initial_capital, version = 1, mora = false, status = ACTIVE

-- Verify initial_capital immutability field
SELECT initial_capital = pending_capital AS matches_on_creation
FROM credits WHERE id = '<credit_id>';
-- Expected: true
```

---

### Step 4: Installment Generation

| # | Action | Expected | Pass | Fail | Notes |
|---|--------|----------|------|------|-------|
| 4.1 | Trigger period job (cron or manual call) OR advance `next_period_date` to today via direct DB update for testing | Installment created for credit | | | |
| 4.2 | GET `/credits/<credit_id>/installments` | List contains installment with `status = UPCOMING` | | | |
| 4.3 | Verify `interest_portion` formula: `pending_capital * (annual_rate/100) / 12` (for MONTHLY) | Calculated value matches stored value | | | |
| 4.4 | Verify `principal_portion` locked at creation | Value does not change on repeated GETs | | | |
| 4.5 | `expected_value = principal_portion + interest_portion` | Sum correct | | | |
| 4.6 | Set credit mora = true manually; trigger period job | NO new installment generated | | | |
| 4.7 | Verify `period_number` is sequential (1, 2, 3...) | No gaps | | | |

**DB Query — Step 4:**
```sql
-- Verify installment locked values
SELECT id, period_number, expected_date, expected_value,
       principal_portion, interest_portion, paid_value, is_overdue, status
FROM installments
WHERE credit_id = '<credit_id>'
ORDER BY period_number;

-- Verify interest formula (MONTHLY example: 12 periods/year)
SELECT
  i.interest_portion,
  c.pending_capital * (c.annual_interest_rate / 100.0) / 12 AS expected_interest,
  ABS(i.interest_portion - (c.pending_capital * (c.annual_interest_rate / 100.0) / 12)) < 0.01 AS matches
FROM installments i
JOIN credits c ON c.id = i.credit_id
WHERE i.credit_id = '<credit_id>'
ORDER BY i.period_number;
-- Expected: matches = true for all rows

-- Verify no installment generated when mora = true
SELECT COUNT(*) FROM installments
WHERE credit_id = '<credit_id>'
AND created_at > NOW() - INTERVAL '1 minute';
-- Expected: 0 (if mora was true when job ran)
```

---

### Step 5: Partial Payment + Mandatory Order

| # | Action | Expected | Pass | Fail | Notes |
|---|--------|----------|------|------|-------|
| 5.1 | Create credit with 2+ overdue installments (advance dates in test DB) | `mora = true` on GET | | | |
| 5.2 | POST `/credits/<credit_id>/payments` with partial amount (e.g. covers overdue interest only) | 200 — payment applied to overdue interest first | | | |
| 5.3 | Verify `applied_to` in payment response: `[{type: "OVERDUE_INTEREST", amount: X}]` | Breakdown correct | | | |
| 5.4 | Check installment with lowest interest: `paid_value` incremented | Correct target | | | |
| 5.5 | Send payment covering overdue interest + partial overdue principal | `applied_to` shows both types in order | | | |
| 5.6 | Verify `credit.pending_capital` reduced only by principal applied, not by interest | Capital unchanged for interest-only payment | | | |
| 5.7 | Fully pay all overdue installments | `credit.mora = false`, `mora_since = null` | | | |
| 5.8 | Verify `credit.version` incremented on each payment | Optimistic lock working | | | |

**DB Query — Step 5:**
```sql
-- Verify payment breakdown stored
SELECT id, amount, applied_to, payment_date, created_at
FROM payments
WHERE credit_id = '<credit_id>'
ORDER BY created_at DESC LIMIT 1;
-- applied_to should be JSONB array with types: OVERDUE_INTEREST, OVERDUE_PRINCIPAL, FUTURE_PRINCIPAL

-- Verify installment state after partial payment
SELECT id, period_number, expected_value, paid_value,
       (expected_value - paid_value) AS remaining,
       status, is_overdue
FROM installments
WHERE credit_id = '<credit_id>'
ORDER BY period_number;
-- PARTIALLY_PAID installments: 0 < paid_value < expected_value

-- Verify capital impact: only principal reduces pending_capital
SELECT
  c.initial_capital,
  c.pending_capital,
  c.initial_capital - c.pending_capital AS total_principal_paid,
  (SELECT COALESCE(SUM((elem->>'amount')::decimal), 0)
   FROM payments p, jsonb_array_elements(p.applied_to) elem
   WHERE p.credit_id = c.id
   AND elem->>'type' IN ('OVERDUE_PRINCIPAL','FUTURE_PRINCIPAL')) AS principal_from_payments
FROM credits c
WHERE c.id = '<credit_id>';
-- Expected: total_principal_paid = principal_from_payments

-- Verify payment mandatory order: no future_principal paid before overdue_interest
SELECT p.id,
  (SELECT SUM((elem->>'amount')::decimal) FROM jsonb_array_elements(p.applied_to) elem WHERE elem->>'type' = 'OVERDUE_INTEREST') AS overdue_interest_applied,
  (SELECT SUM((elem->>'amount')::decimal) FROM jsonb_array_elements(p.applied_to) elem WHERE elem->>'type' = 'FUTURE_PRINCIPAL') AS future_principal_applied
FROM payments p
WHERE p.credit_id = '<credit_id>';
-- If overdue_interest was >0 on that payment, future_principal should be 0 unless interest fully covered
```

---

### Step 6: Mora Detection (Time-Travel)

| # | Action | Expected | Pass | Fail | Notes |
|---|--------|----------|------|------|-------|
| 6.1 | Set installment `expected_date` to past date in test DB: `UPDATE installments SET expected_date = NOW() - INTERVAL '5 days' WHERE id = '<id>'` | Row updated | | | |
| 6.2 | GET `/credits/<credit_id>` | Response: `mora = true`, `mora_since = <earliest overdue date>` | | | |
| 6.3 | UI: mora indicator shown on credit card | Visual flag visible | | | |
| 6.4 | UI: `days_overdue` = today - mora_since | Correct calculation displayed | | | |
| 6.5 | Trigger period job while mora = true | NO new installment generated, installment count unchanged | | | |
| 6.6 | Verify NO penalty columns, NO extra interest rows | Only informational mora flag | | | |
| 6.7 | Pay all overdue installments to full | `mora = false`, `mora_since = null`, UI clears | | | |
| 6.8 | Create 2 overdue installments; GET credit | `mora_since` = earliest of the two dates | | | |

**DB Query — Step 6:**
```sql
-- Simulate overdue (test only — direct DB manipulation):
UPDATE installments
SET expected_date = CURRENT_DATE - INTERVAL '5 days'
WHERE id = '<installment_id>';

-- Verify mora state after GET (mora recalculated on credit.get()):
SELECT mora, mora_since
FROM credits
WHERE id = '<credit_id>';
-- Expected: mora = true, mora_since = date of earliest overdue installment

-- Verify no penalty interest or extra records created during mora:
SELECT COUNT(*) FROM installments
WHERE credit_id = '<credit_id>'
AND created_at > '<mora_start_timestamp>';
-- Expected: 0 new installments while mora active

-- Verify no new columns with penalty amounts:
SELECT interest_portion, expected_value FROM installments
WHERE credit_id = '<credit_id>'
AND is_overdue = true;
-- interest_portion must not have changed from original locked value

-- Confirm mora_since = earliest overdue date:
SELECT MIN(expected_date) AS earliest_overdue
FROM installments
WHERE credit_id = '<credit_id>'
AND is_overdue = true
AND status != 'PAID';
-- Compare against credits.mora_since — must match
```

---

### Step 7: Savings + Liquidation

| # | Action | Expected | Pass | Fail | Notes |
|---|--------|----------|------|------|-------|
| 7.1 | POST `/clients/<client_id>/savings` three times: `{contribution_amount: 500, contribution_date: "<date>"}` | 3 records created with `status = ACTIVE` | | | |
| 7.2 | UI: contributions list shows all 3 entries with amounts and dates | Correct display | | | |
| 7.3 | POST `/clients/<client_id>/savings/liquidate` | 200 — liquidation record returned | | | |
| 7.4 | Verify `total_contributions = 1500.00` | Sum correct | | | |
| 7.5 | Verify `interest_earned = 1500 * (SAVINGS_RATE/100)` | Formula applied correctly | | | |
| 7.6 | Verify `total_delivered = total_contributions + interest_earned` | Total correct | | | |
| 7.7 | Verify `interest_rate` in liquidation record = current `SAVINGS_RATE` env var (rate snapshot) | Immutable snapshot stored | | | |
| 7.8 | All 3 contributions: `status = LIQUIDATED`, `liquidated_at` set | Atomic state change | | | |
| 7.9 | POST another liquidation immediately after | 400/409 — no ACTIVE contributions remain | | | |
| 7.10 | Check FinancialHistory: `SAVINGS_LIQUIDATION` event logged | History record exists | | | |

**DB Query — Step 7:**
```sql
-- Verify contributions exist and are ACTIVE before liquidation:
SELECT id, contribution_amount, contribution_date, status
FROM savings
WHERE client_id = '<client_id>'
AND status = 'ACTIVE';

-- After liquidation: verify all LIQUIDATED
SELECT id, contribution_amount, status, liquidated_at
FROM savings
WHERE client_id = '<client_id>';
-- Expected: all status = LIQUIDATED, liquidated_at not null

-- Verify liquidation record accuracy:
SELECT sl.total_contributions,
       sl.interest_earned,
       sl.total_delivered,
       sl.interest_rate,
       sl.total_contributions * (sl.interest_rate / 100.0) AS calculated_interest,
       ABS(sl.interest_earned - sl.total_contributions * (sl.interest_rate / 100.0)) < 0.01 AS interest_correct,
       ABS(sl.total_delivered - (sl.total_contributions + sl.interest_earned)) < 0.01 AS total_correct
FROM savings_liquidations sl
WHERE sl.client_id = '<client_id>'
ORDER BY sl.created_at DESC LIMIT 1;
-- Expected: interest_correct = true, total_correct = true

-- Verify history event:
SELECT event_type, amount, description, timestamp
FROM financial_history
WHERE client_id = '<client_id>'
AND event_type = 'SAVINGS_LIQUIDATION'
ORDER BY timestamp DESC LIMIT 1;
-- Expected: 1 row
```

---

## SECTION 2 — MANUAL TEST CASES

### TC-001: Full Happy Path (Auth → Credit → Pay → Close)

**Preconditions:** Clean DB, no existing users  
**Steps:**
1. Register user via UI registration form
2. Login and verify JWT in localStorage
3. Create client with full data (all optional fields)
4. Create MONTHLY credit: initial_capital=2000, rate=24%, start_date=today
5. Trigger installment generation (advance next_period_date to today)
6. Register payment equal to expected_value of first installment
7. Verify installment status = PAID, pending_capital reduced by principal_portion
8. Pay all remaining installments
9. Verify credit auto-closes (status = CLOSED, pending_capital = 0)

**Expected:** Full lifecycle completes without error. All DB values consistent with formulas.

---

### TC-002: Payment Mandatory Order Enforcement

**Preconditions:** Credit with 2 overdue installments + 1 future installment  
**Steps:**
1. Create credit, generate 3 installments
2. Backdate `expected_date` of first 2 installments to past
3. GET credit — mora = true
4. Send payment = overdue_interest of installment 1 only
5. Verify ONLY overdue_interest credited, no overdue_principal touched
6. Send payment = overdue_interest of installment 2 + overdue_principal of installment 1
7. Verify correct order: interest fully absorbed before principal

**Expected:** `applied_to` JSONB always shows correct type ordering.

---

### TC-003: Overpayment → Auto-Close

**Preconditions:** Credit with pending_capital = 500, 1 unpaid installment of 550  
**Steps:**
1. Send payment = 1000 (exceeds total debt)
2. Verify all installments PAID
3. Verify pending_capital = 0
4. Verify credit status = CLOSED
5. UI: credit shows as CLOSED with closed_date set

**Expected:** No orphaned pending_capital. Credit cleanly closed. History event logged.

---

### TC-004: Payment < Single Interest (Minimum Payment)

**Preconditions:** Installment with interest_portion = 50.00  
**Steps:**
1. Send payment = 10.00 (less than interest_portion)
2. Verify installment.paid_value = 10.00
3. Verify installment.status = PARTIALLY_PAID
4. Verify no overdue_principal or future_principal touched
5. Verify pending_capital unchanged

**Expected:** Remainder stays in installment. No schedule recalc.

---

### TC-005: Cross-User Isolation (Security)

**Preconditions:** USER_A has client + credit; USER_B is separate user  
**Steps:**
1. Login as USER_B
2. GET `/clients/<user_a_client_id>` — should return 403/404
3. POST `/credits/<user_a_credit_id>/payments` — should return 403/404
4. GET `/clients` — must return empty or only USER_B's data
5. GET `/credits/<user_a_credit_id>/installments` — 403/404

**Expected:** RLS enforced. Zero data leak between users.

---

### TC-006: Savings Liquidation with Varying Contributions

**Preconditions:** Client with contributions of 100, 250, 400, 750  
**Steps:**
1. Create 4 contributions with different amounts and dates
2. Verify `total_contributions = 1500`
3. Liquidate
4. Verify `interest_earned` = 1500 * rate / 100
5. Verify `total_delivered` = 1500 + interest_earned
6. Verify rate snapshot matches `SAVINGS_RATE` env at time of liquidation

**Expected:** Formula correct regardless of number/size of contributions.

---

### TC-007: Multiple Overdue Installments — mora_since = Earliest

**Preconditions:** 3 installments with expected_dates: 10 days ago, 5 days ago, 2 days ago  
**Steps:**
1. Backdate all three installments
2. GET credit
3. Verify `mora = true`
4. Verify `mora_since` = date from 10 days ago (NOT 5 or 2)

**Expected:** mora_since always points to earliest overdue, not most recent.

---

## SECTION 3 — DB VERIFICATION QUERIES (MASTER SET)

```sql
-- ============================================================
-- GLOBAL CONSISTENCY CHECKS (run after any operation)
-- ============================================================

-- 1. Capital drift: pending_capital should equal initial_capital minus principal paid
SELECT
  c.id,
  c.initial_capital,
  c.pending_capital,
  c.initial_capital - COALESCE(principal_paid.total, 0) AS expected_pending,
  ABS(c.pending_capital - (c.initial_capital - COALESCE(principal_paid.total, 0))) < 0.01 AS capital_consistent
FROM credits c
LEFT JOIN (
  SELECT p.credit_id,
    SUM((elem->>'amount')::decimal) AS total
  FROM payments p, jsonb_array_elements(p.applied_to) elem
  WHERE elem->>'type' IN ('OVERDUE_PRINCIPAL','FUTURE_PRINCIPAL')
  GROUP BY p.credit_id
) principal_paid ON principal_paid.credit_id = c.id;

-- 2. Interest double-count: verify interest_portion never used as base for next installment
-- All installments for a credit should have interest = pending_capital_AT_CREATION * rate / periods
-- (Manual review: query installments, check values match spec formula)
SELECT
  i.id, i.period_number, i.interest_portion,
  c.annual_interest_rate,
  -- For MONTHLY (12 periods), adjust divisor per periodicity
  CASE c.periodicity
    WHEN 'MONTHLY' THEN c.pending_capital * (c.annual_interest_rate / 100.0) / 12
    WHEN 'WEEKLY' THEN c.pending_capital * (c.annual_interest_rate / 100.0) / 52
    WHEN 'BIWEEKLY' THEN c.pending_capital * (c.annual_interest_rate / 100.0) / 26
    WHEN 'DAILY' THEN c.pending_capital * (c.annual_interest_rate / 100.0) / 365
  END AS naive_expected
FROM installments i
JOIN credits c ON c.id = i.credit_id
ORDER BY i.credit_id, i.period_number;

-- 3. Stale mora: mora = true but no overdue unpaid installments
SELECT c.id, c.mora, c.mora_since,
  COUNT(i.id) FILTER (WHERE i.is_overdue = true AND i.status != 'PAID') AS actual_overdue_count
FROM credits c
LEFT JOIN installments i ON i.credit_id = c.id
GROUP BY c.id, c.mora, c.mora_since
HAVING c.mora = true AND COUNT(i.id) FILTER (WHERE i.is_overdue = true AND i.status != 'PAID') = 0;
-- Expected: 0 rows (stale mora = bug)

-- 4. Orphan installments: installments with no parent credit
SELECT i.id, i.credit_id FROM installments i
LEFT JOIN credits c ON c.id = i.credit_id
WHERE c.id IS NULL;
-- Expected: 0 rows

-- 5. Orphan payments: payments with no parent credit
SELECT p.id, p.credit_id FROM payments p
LEFT JOIN credits c ON c.id = p.credit_id
WHERE c.id IS NULL;
-- Expected: 0 rows

-- 6. Cross-user data leak: clients not owned by any user (RLS gap)
SELECT id, first_name, phone FROM clients
WHERE user_id IS NULL AND deleted_at IS NULL;
-- Expected: 0 rows

-- 7. Orphan history: financial_history records with client_id not in clients
SELECT fh.id, fh.event_type, fh.client_id FROM financial_history fh
LEFT JOIN clients c ON c.id = fh.client_id
WHERE c.id IS NULL;
-- Expected: 0 rows (soft-deleted clients should still have id)

-- 8. Installment paid_value exceeds expected_value (overpayment leak)
SELECT id, period_number, expected_value, paid_value
FROM installments
WHERE paid_value > expected_value + 0.01;
-- Expected: 0 rows

-- 9. Status inconsistency: status=PAID but paid_value < expected_value
SELECT id, period_number, expected_value, paid_value, status
FROM installments
WHERE status = 'PAID' AND paid_value < expected_value - 0.01;
-- Expected: 0 rows

-- 10. Status inconsistency: status=PARTIALLY_PAID but paid_value = 0 or >= expected
SELECT id, period_number, expected_value, paid_value, status
FROM installments
WHERE status = 'PARTIALLY_PAID'
  AND (paid_value <= 0 OR paid_value >= expected_value - 0.01);
-- Expected: 0 rows

-- 11. Missing history for payments
SELECT p.id, p.credit_id, p.created_at
FROM payments p
WHERE NOT EXISTS (
  SELECT 1 FROM financial_history fh
  WHERE fh.event_type = 'PAYMENT_RECORDED'
  AND fh.metadata->>'payment_id' = p.id::text
);
-- Expected: 0 rows

-- 12. Credit version not incrementing (concurrency check)
SELECT id, version, updated_at FROM credits
WHERE version < 1;
-- Expected: 0 rows (all credits start at version=1 minimum)

-- 13. Savings liquidation: total_delivered mismatch
SELECT sl.id,
  sl.total_contributions + sl.interest_earned AS expected_total,
  sl.total_delivered,
  ABS(sl.total_delivered - (sl.total_contributions + sl.interest_earned)) < 0.01 AS consistent
FROM savings_liquidations sl
WHERE ABS(sl.total_delivered - (sl.total_contributions + sl.interest_earned)) >= 0.01;
-- Expected: 0 rows

-- 14. ACTIVE contributions after liquidation (incomplete atomic transaction)
SELECT s.client_id, COUNT(*) AS active_after_liquidation
FROM savings s
WHERE s.status = 'ACTIVE'
AND EXISTS (
  SELECT 1 FROM savings_liquidations sl
  WHERE sl.client_id = s.client_id
  AND sl.liquidation_date <= s.contribution_date
)
GROUP BY s.client_id;
-- Expected: 0 rows
```

---

## SECTION 4 — INCONSISTENCY HUNT LIST

| # | Inconsistency | Where to Look | SQL Check # | Severity |
|---|---------------|---------------|-------------|----------|
| I-01 | Capital drift — pending_capital != initial - principal paid | credits, payments | Query 1 | CRITICAL |
| I-02 | Interest double-count — interest calculated on prior interest | installments, credits | Query 2 | CRITICAL |
| I-03 | Stale mora — mora=true but no overdue unpaid installments | credits, installments | Query 3 | HIGH |
| I-04 | New installments generated during mora | installments | Step 6 queries | HIGH |
| I-05 | Orphan installments after credit delete | installments | Query 4 | MEDIUM |
| I-06 | Orphan payments after credit delete | payments | Query 5 | MEDIUM |
| I-07 | Cross-user data leak (RLS failure) | clients, credits | Query 6 + TC-005 | CRITICAL |
| I-08 | Orphan financial_history after client soft-delete | financial_history | Query 7 | MEDIUM |
| I-09 | paid_value > expected_value (overpayment leak) | installments | Query 8 | HIGH |
| I-10 | PAID status but paid_value < expected | installments | Query 9 | HIGH |
| I-11 | PARTIALLY_PAID with paid_value = 0 | installments | Query 10 | MEDIUM |
| I-12 | Payment with no history event | payments, financial_history | Query 11 | HIGH |
| I-13 | Mandatory order violated (future principal before overdue interest) | payments.applied_to | Step 5 DB query | CRITICAL |
| I-14 | mora_since not = earliest overdue (wrong date) | credits | Step 6 + TC-007 | HIGH |
| I-15 | Savings liquidation total_delivered mismatch | savings_liquidations | Query 13 | HIGH |
| I-16 | ACTIVE contributions after liquidation (non-atomic transaction) | savings | Query 14 | HIGH |
| I-17 | Credit version not incremented on payment | credits | Query 12 | MEDIUM |
| I-18 | Penalty interest or extra installments during mora | installments | Step 6 queries | CRITICAL |
| I-19 | Savings interest_rate not snapshotted (uses live env var at query time) | savings_liquidations | Step 7 DB query | HIGH |
| I-20 | Interest accrual after mora cleared not resuming correctly | installments | New installment after mora=false | HIGH |

---

## SECTION 5 — PASS/FAIL TRACKING

| Step | Description | Status | Tester | Date | Notes |
|------|-------------|--------|--------|------|-------|
| 1 | Register + Login | | | | |
| 2 | Create Client | | | | |
| 3 | Create Credit | | | | |
| 4 | Installment Generation | | | | |
| 5 | Partial Payment + Mandatory Order | | | | |
| 6 | Mora Detection (Time-Travel) | | | | |
| 7 | Savings + Liquidation | | | | |
| TC-001 | Full Happy Path | | | | |
| TC-002 | Mandatory Order Enforcement | | | | |
| TC-003 | Overpayment Auto-Close | | | | |
| TC-004 | Payment < Single Interest | | | | |
| TC-005 | Cross-User Isolation | | | | |
| TC-006 | Savings N Contributions | | | | |
| TC-007 | mora_since = Earliest | | | | |
| I-01 to I-20 | Inconsistency Hunt (all queries return 0 rows) | | | | |

---

## KNOWN GAPS / ASSUMPTIONS

1. **Period job endpoint**: Spec defines a daily cron for installment generation but no explicit HTTP trigger endpoint is documented. Test Step 4 requires either a cron trigger URL or direct DB `next_period_date` manipulation.
2. **Supabase RLS session context**: Queries using `SET LOCAL "request.jwt.claim.sub"` require Supabase PostgREST or equivalent session setup. Adjust syntax per actual Supabase RLS policy implementation.
3. **SAVINGS_RATE env var**: Must be confirmed in running environment before Step 7. Check with `echo $SAVINGS_RATE` or query app config endpoint.
4. **Auth provider**: Spec references Firebase Admin SDK for token verification AND Supabase Auth. Step 1 queries assume Supabase `auth.users` table. Confirm actual provider.
5. **Token refresh mechanism**: Step 1.5 requires near-expiry simulation. Confirm token TTL and refresh endpoint path.
