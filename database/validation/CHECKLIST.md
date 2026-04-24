# Natillera PWA — Supabase/Postgres DB Validation Checklist
<!-- Generated: 2026-04-23 | Based on migrations 001–003 -->

> Run every query in Supabase SQL Editor (Dashboard > SQL Editor) or pipe `run_all.sql` to psql.
> Queries that simulate RLS context use `SET LOCAL` — wrap them in a transaction block as shown.

---

## How to Interpret Error Codes

| SQLSTATE | Name | Meaning |
|----------|------|---------|
| `42501` | `insufficient_privilege` | RLS blocked the operation (no matching policy) |
| `P0001` | `raise_exception` | Trigger fired RAISE EXCEPTION |
| `23503` | `foreign_key_violation` | FK constraint rejected the row |
| `23505` | `unique_violation` | UNIQUE constraint rejected the row |
| `23502` | `not_null_violation` | NOT NULL constraint rejected the row |
| `23514` | `check_violation` | CHECK constraint rejected the value |

---

## PHASE 1 — STRUCTURE

### 1.1 All 8 tables exist

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'users','clients','credits','installments',
    'payments','savings','savings_liquidations','financial_history'
  )
ORDER BY table_name;
```

**Expected:** 8 rows, one per table name above.

---

### 1.2 Foreign keys — user_id on all domain tables

```sql
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_schema AS foreign_schema,
  ccu.table_name   AS foreign_table,
  ccu.column_name  AS foreign_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
  AND kcu.column_name = 'user_id'
ORDER BY tc.table_name;
```

**Expected:** 7 rows (all domain tables except `public.users` itself).
Tables: `clients`, `credits`, `financial_history`, `installments`, `payments`, `savings`, `savings_liquidations`.
Each row shows `foreign_table = users` and `foreign_column = id` pointing to `auth.users`.

---

### 1.3 Additional FK — client_id and credit_id chains

```sql
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_name AS foreign_table
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
  AND kcu.column_name IN ('client_id','credit_id')
ORDER BY tc.table_name, kcu.column_name;
```

**Expected minimum rows:**
- `credits.client_id` → `clients`
- `financial_history.client_id` → `clients`
- `financial_history.credit_id` → `credits`
- `installments.credit_id` → `credits`
- `payments.credit_id` → `credits`
- `savings.client_id` → `clients`
- `savings_liquidations.client_id` → `clients`

---

### 1.4 Indexes present

```sql
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN (
    'users','clients','credits','installments',
    'payments','savings','savings_liquidations','financial_history'
  )
ORDER BY tablename, indexname;
```

**Expected — at minimum these named indexes:**
`idx_clients_deleted`, `idx_clients_user`, `idx_credits_client`, `idx_credits_mora`, `idx_credits_status`, `idx_credits_user`, `idx_financial_history_client`, `idx_financial_history_created_at`, `idx_financial_history_event_type`, `idx_financial_history_user`, `idx_installments_credit`, `idx_installments_expected_date`, `idx_installments_is_overdue`, `idx_installments_user`, `idx_payments_credit`, `idx_payments_date`, `idx_payments_user`, `idx_savings_client`, `idx_savings_liquidations_client`, `idx_savings_liquidations_user`, `idx_savings_status`, `idx_savings_user`, `idx_users_created_at`, `idx_users_email`.

---

### 1.5 NOT NULL constraints on key columns

```sql
SELECT table_name, column_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
    (table_name = 'clients'  AND column_name IN ('user_id','first_name','last_name','phone')) OR
    (table_name = 'credits'  AND column_name IN ('user_id','client_id','initial_capital','pending_capital','periodicity','annual_interest_rate','status','start_date')) OR
    (table_name = 'installments' AND column_name IN ('user_id','credit_id','period_number','expected_date','expected_value','principal_portion','interest_portion','status')) OR
    (table_name = 'payments' AND column_name IN ('user_id','credit_id','amount','payment_date','applied_to','recorded_by')) OR
    (table_name = 'savings'  AND column_name IN ('user_id','client_id','contribution_amount','contribution_date','status')) OR
    (table_name = 'savings_liquidations' AND column_name IN ('user_id','client_id','total_contributions','interest_earned','total_delivered','interest_rate','liquidation_date')) OR
    (table_name = 'financial_history' AND column_name IN ('user_id','event_type','client_id','description','operator_id'))
  )
  AND is_nullable = 'YES';
```

**Expected:** 0 rows. Any row returned means a NOT NULL was not applied.

---

### 1.6 CHECK constraints exist on critical columns

```sql
SELECT
  tc.table_name,
  tc.constraint_name,
  cc.check_clause
FROM information_schema.table_constraints AS tc
JOIN information_schema.check_constraints AS cc
  ON tc.constraint_name = cc.constraint_name
WHERE tc.table_schema = 'public'
  AND tc.constraint_type = 'CHECK'
ORDER BY tc.table_name, tc.constraint_name;
```

**Expected:** Constraints covering `periodicity IN (...)`, `status IN (...)`, `initial_capital > 0`, `pending_capital >= 0`, `expected_value > 0`, `amount > 0`, `notes length <= 500`, `event_type IN (...)`, etc.

---

### 1.7 UNIQUE constraint — installments (credit_id, period_number)

```sql
SELECT tc.table_name, kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'UNIQUE'
  AND tc.table_schema = 'public'
  AND tc.table_name = 'installments'
ORDER BY kcu.ordinal_position;
```

**Expected:** 2 rows — `credit_id` and `period_number` as part of the same composite unique constraint.

---

## PHASE 2 — RLS

### 2.1 RLS enabled on all 8 tables

```sql
SELECT relname AS table_name, relrowsecurity AS rls_enabled
FROM pg_class
WHERE relnamespace = 'public'::regnamespace
  AND relname IN (
    'users','clients','credits','installments',
    'payments','savings','savings_liquidations','financial_history'
  )
ORDER BY relname;
```

**Expected:** 8 rows, all with `rls_enabled = true`.

---

### 2.2 List all RLS policies

```sql
SELECT tablename, policyname, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd;
```

**Expected:** Minimum 30 policies total.
- `users`: 3 (SELECT, INSERT, UPDATE)
- `clients`, `credits`, `installments`, `payments`, `savings`, `savings_liquidations`: 4 each (SELECT, INSERT, UPDATE, DELETE)
- `financial_history`: 2 (SELECT, INSERT) — NO UPDATE or DELETE policy

---

### 2.3 financial_history has NO UPDATE/DELETE policy

```sql
SELECT policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename = 'financial_history'
  AND cmd IN ('UPDATE','DELETE');
```

**Expected:** 0 rows. Any row returned means the append-only guarantee is broken.

---

### 2.4 RLS isolation — User A cannot read User B rows (clients example)

Replace `<USER_A_UUID>` and `<USER_B_UUID>` with real UUIDs from your test data.

```sql
-- Setup: insert one client for each user first (run as service_role / postgres)
-- Then simulate authenticated session as User A:

BEGIN;
  SET LOCAL role = 'authenticated';
  SELECT set_config('request.jwt.claims', '{"sub":"<USER_A_UUID>"}', true);

  -- Should return ONLY User A's clients
  SELECT id, user_id, first_name FROM clients;
ROLLBACK;
```

**Expected:** Only rows where `user_id = <USER_A_UUID>`. Zero rows belonging to User B.

---

### 2.5 User A cannot INSERT a row with User B's user_id

```sql
BEGIN;
  SET LOCAL role = 'authenticated';
  SELECT set_config('request.jwt.claims', '{"sub":"<USER_A_UUID>"}', true);

  INSERT INTO clients (user_id, first_name, last_name, phone)
  VALUES ('<USER_B_UUID>', 'Attacker', 'Test', '0000000000');
ROLLBACK;
```

**Expected:** ERROR with SQLSTATE `42501` (`insufficient_privilege`). Insert blocked by RLS `WITH CHECK`.

---

### 2.6 User A cannot UPDATE User B's client

```sql
BEGIN;
  SET LOCAL role = 'authenticated';
  SELECT set_config('request.jwt.claims', '{"sub":"<USER_A_UUID>"}', true);

  -- Provide a known client_id owned by User B
  UPDATE clients SET first_name = 'Hacked' WHERE id = '<USER_B_CLIENT_UUID>';
  -- Check 0 rows updated (RLS silently filters; no error but no effect)
  SELECT COUNT(*) FROM clients WHERE id = '<USER_B_CLIENT_UUID>' AND first_name = 'Hacked';
ROLLBACK;
```

**Expected:** UPDATE affects 0 rows. SELECT returns 0 (RLS hides User B's row entirely).

---

## PHASE 3 — TRIGGERS

### 3.1 updated_at auto-stamp on UPDATE

```sql
-- Run as postgres / service_role
DO $$
DECLARE
  v_id UUID;
  v_before TIMESTAMP;
  v_after  TIMESTAMP;
BEGIN
  -- Insert a test client (bypassing RLS via service_role)
  INSERT INTO clients (user_id, first_name, last_name, phone)
  VALUES (
    (SELECT id FROM auth.users LIMIT 1),
    'Trigger', 'Test', '9999999991'
  )
  RETURNING id INTO v_id;

  SELECT updated_at INTO v_before FROM clients WHERE id = v_id;
  PERFORM pg_sleep(0.05);

  UPDATE clients SET first_name = 'Triggered' WHERE id = v_id;
  SELECT updated_at INTO v_after FROM clients WHERE id = v_id;

  IF v_after > v_before THEN
    RAISE NOTICE 'PASS: updated_at advanced from % to %', v_before, v_after;
  ELSE
    RAISE EXCEPTION 'FAIL: updated_at did not advance (before=%, after=%)', v_before, v_after;
  END IF;

  DELETE FROM clients WHERE id = v_id;
END $$;
```

**Expected:** `NOTICE: PASS: updated_at advanced from … to …`

---

### 3.2 Installment locked fields reject UPDATE

Test each locked field. Expected SQLSTATE: `P0001`.

```sql
-- Step 1: get a real installment id (or insert one as service_role)
-- Step 2: attempt to change a locked field

UPDATE installments
SET expected_value = 9999.00
WHERE id = '<INSTALLMENT_UUID>';
```

**Expected:** `ERROR: installment.expected_value is immutable after creation` (SQLSTATE `P0001`)

```sql
UPDATE installments
SET principal_portion = 9999.00
WHERE id = '<INSTALLMENT_UUID>';
```

**Expected:** `ERROR: installment.principal_portion is immutable after creation` (SQLSTATE `P0001`)

```sql
UPDATE installments
SET interest_portion = 9999.00
WHERE id = '<INSTALLMENT_UUID>';
```

**Expected:** `ERROR: installment.interest_portion is immutable after creation` (SQLSTATE `P0001`)

```sql
UPDATE installments
SET period_number = 999
WHERE id = '<INSTALLMENT_UUID>';
```

**Expected:** `ERROR: installment.period_number is immutable after creation` (SQLSTATE `P0001`)

```sql
UPDATE installments
SET expected_date = '2099-01-01'
WHERE id = '<INSTALLMENT_UUID>';
```

**Expected:** `ERROR: installment.expected_date is immutable after creation` (SQLSTATE `P0001`)

Non-locked fields should still update without error:

```sql
UPDATE installments
SET status = 'PARTIALLY_PAID', paid_value = 100.00
WHERE id = '<INSTALLMENT_UUID>';
```

**Expected:** `UPDATE 1` — no error.

---

### 3.3 financial_history is append-only (UPDATE blocked by trigger)

```sql
UPDATE financial_history
SET description = 'tampered'
WHERE id = '<HISTORY_UUID>';
```

**Expected:** `ERROR: financial_history is immutable. Updates are not allowed.` (SQLSTATE `P0001`)

```sql
DELETE FROM financial_history
WHERE id = '<HISTORY_UUID>';
```

**Expected:** `ERROR: financial_history is immutable. Updates are not allowed.` (SQLSTATE `P0001`)

---

### 3.4 Installment user_id auto-synced from parent credit

```sql
-- Insert an installment WITHOUT setting user_id explicitly
-- The trigger sync_installment_user_id must fill it from credits.user_id

DO $$
DECLARE
  v_credit_id UUID;
  v_credit_user UUID;
  v_inst_id UUID;
  v_inst_user UUID;
BEGIN
  SELECT id, user_id INTO v_credit_id, v_credit_user FROM credits LIMIT 1;

  INSERT INTO installments (credit_id, period_number, expected_date, expected_value, principal_portion, interest_portion)
  VALUES (v_credit_id, 9999, CURRENT_DATE + 30, 100.00, 80.00, 20.00)
  RETURNING id INTO v_inst_id;

  SELECT user_id INTO v_inst_user FROM installments WHERE id = v_inst_id;

  IF v_inst_user = v_credit_user THEN
    RAISE NOTICE 'PASS: installment.user_id = % (matches credit)', v_inst_user;
  ELSE
    RAISE EXCEPTION 'FAIL: installment.user_id=% does not match credit.user_id=%', v_inst_user, v_credit_user;
  END IF;

  DELETE FROM installments WHERE id = v_inst_id;
END $$;
```

**Expected:** `NOTICE: PASS: installment.user_id = <uuid> (matches credit)`

---

### 3.5 Payment user_id auto-synced from parent credit

```sql
DO $$
DECLARE
  v_credit_id UUID;
  v_credit_user UUID;
  v_pay_id UUID;
  v_pay_user UUID;
BEGIN
  SELECT id, user_id INTO v_credit_id, v_credit_user FROM credits LIMIT 1;

  INSERT INTO payments (credit_id, amount, payment_date, applied_to, recorded_by)
  VALUES (v_credit_id, 50.00, CURRENT_DATE, '[]'::jsonb, 'test_operator')
  RETURNING id INTO v_pay_id;

  SELECT user_id INTO v_pay_user FROM payments WHERE id = v_pay_id;

  IF v_pay_user = v_credit_user THEN
    RAISE NOTICE 'PASS: payment.user_id = % (matches credit)', v_pay_user;
  ELSE
    RAISE EXCEPTION 'FAIL: payment.user_id=% does not match credit.user_id=%', v_pay_user, v_credit_user;
  END IF;

  DELETE FROM payments WHERE id = v_pay_id;
END $$;
```

**Expected:** `NOTICE: PASS: payment.user_id = <uuid> (matches credit)`

---

## PHASE 4 — FAILURE FORCING

### 4.1 FK violation — insert credit with non-existent client_id

```sql
INSERT INTO credits (
  user_id, client_id, initial_capital, pending_capital,
  periodicity, annual_interest_rate, status, start_date
) VALUES (
  (SELECT id FROM auth.users LIMIT 1),
  '00000000-0000-0000-0000-000000000000',  -- fake client_id
  1000.00, 1000.00, 'MONTHLY', 12.00, 'ACTIVE', CURRENT_DATE
);
```

**Expected:** `ERROR: insert or update on table "credits" violates foreign key constraint` (SQLSTATE `23503`)

---

### 4.2 FK violation — insert installment with non-existent credit_id

```sql
INSERT INTO installments (credit_id, period_number, expected_date, expected_value, principal_portion, interest_portion)
VALUES (
  '00000000-0000-0000-0000-000000000000',  -- fake credit_id
  1, CURRENT_DATE, 100.00, 80.00, 20.00
);
```

**Expected:** `ERROR: insert or update on table "installments" violates foreign key constraint` (SQLSTATE `23503`)

---

### 4.3 RLS violation — User A inserts row claiming User B's ownership

```sql
BEGIN;
  SET LOCAL role = 'authenticated';
  SELECT set_config('request.jwt.claims', '{"sub":"<USER_A_UUID>"}', true);

  INSERT INTO credits (
    user_id, client_id, initial_capital, pending_capital,
    periodicity, annual_interest_rate, status, start_date
  )
  SELECT
    '<USER_B_UUID>',
    id,
    500.00, 500.00, 'WEEKLY', 8.00, 'ACTIVE', CURRENT_DATE
  FROM clients WHERE user_id = '<USER_B_UUID>' LIMIT 1;
ROLLBACK;
```

**Expected:** `ERROR: new row violates row-level security policy for table "credits"` (SQLSTATE `42501`)

---

### 4.4 Trigger violation — UPDATE installment locked field

```sql
-- Run without transaction; let it fail
UPDATE installments
SET expected_value = 0.01
WHERE id = (SELECT id FROM installments LIMIT 1);
```

**Expected:** `ERROR: installment.expected_value is immutable after creation` (SQLSTATE `P0001`)

---

### 4.5 Trigger violation — UPDATE financial_history

```sql
UPDATE financial_history
SET operator_id = 'intruder'
WHERE id = (SELECT id FROM financial_history LIMIT 1);
```

**Expected:** `ERROR: financial_history is immutable. Updates are not allowed.` (SQLSTATE `P0001`)

---

### 4.6 Trigger violation — DELETE financial_history

```sql
DELETE FROM financial_history
WHERE id = (SELECT id FROM financial_history LIMIT 1);
```

**Expected:** `ERROR: financial_history is immutable. Updates are not allowed.` (SQLSTATE `P0001`)

---

### 4.7 CHECK violation — invalid periodicity value

```sql
INSERT INTO credits (
  user_id, client_id, initial_capital, pending_capital,
  periodicity, annual_interest_rate, status, start_date
)
SELECT
  user_id, id, 100.00, 100.00,
  'INVALID_PERIOD',  -- not in allowed set
  5.00, 'ACTIVE', CURRENT_DATE
FROM clients LIMIT 1;
```

**Expected:** `ERROR: new row for relation "credits" violates check constraint` (SQLSTATE `23514`)

---

### 4.8 CHECK violation — negative initial_capital

```sql
INSERT INTO credits (
  user_id, client_id, initial_capital, pending_capital,
  periodicity, annual_interest_rate, status, start_date
)
SELECT
  user_id, id, -500.00, 0.00,
  'MONTHLY', 5.00, 'ACTIVE', CURRENT_DATE
FROM clients LIMIT 1;
```

**Expected:** `ERROR: new row for relation "credits" violates check constraint` (SQLSTATE `23514`)

---

### 4.9 UNIQUE violation — duplicate (credit_id, period_number)

```sql
DO $$
DECLARE v_credit_id UUID;
BEGIN
  SELECT id INTO v_credit_id FROM credits LIMIT 1;

  INSERT INTO installments (credit_id, period_number, expected_date, expected_value, principal_portion, interest_portion)
  VALUES (v_credit_id, 1, CURRENT_DATE, 100.00, 80.00, 20.00);

  -- Same combination again:
  INSERT INTO installments (credit_id, period_number, expected_date, expected_value, principal_portion, interest_portion)
  VALUES (v_credit_id, 1, CURRENT_DATE + 1, 200.00, 160.00, 40.00);
END $$;
```

**Expected:** `ERROR: duplicate key value violates unique constraint "installments_credit_id_period_number_key"` (SQLSTATE `23505`)

---

## PHASE 5 — TRIGGER FUNCTIONS EXIST

### 5.1 All trigger functions registered in pg_proc

```sql
SELECT proname AS function_name
FROM pg_proc
WHERE proname IN (
  'set_updated_at',
  'sync_installment_user_id',
  'sync_payment_user_id',
  'sync_savings_user_id',
  'prevent_history_update',
  'protect_installment_locked_fields',
  'handle_new_user'
)
ORDER BY proname;
```

**Expected:** 7 rows, one per function.

---

### 5.2 All triggers registered in pg_trigger

```sql
SELECT tgname AS trigger_name, relname AS table_name
FROM pg_trigger
JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid
WHERE tgname IN (
  'set_updated_at_users',
  'set_updated_at_clients',
  'set_updated_at_credits',
  'installment_user_sync',
  'payment_user_sync',
  'savings_user_sync',
  'savings_liquidations_user_sync',
  'financial_history_immutable',
  'installment_locked_fields',
  'on_auth_user_created'
)
ORDER BY tgname;
```

**Expected:** 10 rows.

---

## Gap Analysis — Known Coverage Gaps

| Gap | Risk | Recommendation |
|-----|------|---------------|
| No `updated_at` trigger on `installments` | `updated_at` column does not exist on `installments` — table has `paid_at` instead. No gap in coverage but verify schema if `updated_at` is ever added | Low |
| `payments` has no `updated_at` column | Payments are insert-only by design; confirm this is intentional | Low |
| `savings` / `savings_liquidations` have no `updated_at` column | Same as payments — verify intentional | Low |
| `financial_history` DELETE blocked by trigger but RLS has no DELETE policy either | Double-guarded — both layers block. Good defense-in-depth | None |
| `handle_new_user` trigger targets `auth.users` | Supabase may restrict triggers on `auth` schema; verify via Dashboard > Database > Triggers | Medium |
| No RLS test for `public.users` isolation | User A should not read User B's profile row | Should add explicit test |
