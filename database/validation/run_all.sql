-- =============================================================
-- run_all.sql — Natillera PWA DB Validation Suite
-- Generated: 2026-04-23
-- Usage:
--   psql "$DATABASE_URL" -f run_all.sql
-- Or paste into Supabase SQL Editor (Dashboard > SQL Editor).
-- Sections that require real UUIDs are marked with TODO comments.
-- =============================================================

\echo ''
\echo '============================================================'
\echo 'PHASE 1 — STRUCTURE'
\echo '============================================================'

-- 1.1 Tables
\echo '1.1 Tables exist (expect 8 rows)'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'users','clients','credits','installments',
    'payments','savings','savings_liquidations','financial_history'
  )
ORDER BY table_name;

-- 1.2 user_id FKs on domain tables
\echo '1.2 user_id foreign keys (expect 7 rows)'
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_schema AS foreign_schema,
  ccu.table_name   AS foreign_table
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

-- 1.3 client_id / credit_id FKs
\echo '1.3 client_id / credit_id FKs (expect 7 rows)'
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

-- 1.4 Indexes
\echo '1.4 Indexes (expect >= 24 rows)'
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN (
    'users','clients','credits','installments',
    'payments','savings','savings_liquidations','financial_history'
  )
ORDER BY tablename, indexname;

-- 1.5 NOT NULL violations (expect 0 rows)
\echo '1.5 NOT NULL check on critical columns (expect 0 rows)'
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

-- 1.6 CHECK constraints
\echo '1.6 CHECK constraints (expect multiple rows covering status, periodicity, amounts)'
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

-- 1.7 Unique constraint on installments
\echo '1.7 Unique(credit_id, period_number) on installments (expect 2 column rows)'
SELECT tc.table_name, kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'UNIQUE'
  AND tc.table_schema = 'public'
  AND tc.table_name = 'installments'
ORDER BY kcu.ordinal_position;

\echo ''
\echo '============================================================'
\echo 'PHASE 2 — RLS'
\echo '============================================================'

-- 2.1 RLS enabled
\echo '2.1 RLS enabled on all tables (expect 8 rows, all true)'
SELECT relname AS table_name, relrowsecurity AS rls_enabled
FROM pg_class
WHERE relnamespace = 'public'::regnamespace
  AND relname IN (
    'users','clients','credits','installments',
    'payments','savings','savings_liquidations','financial_history'
  )
ORDER BY relname;

-- 2.2 All policies listed
\echo '2.2 RLS policies (expect >= 30 rows)'
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd;

-- 2.3 financial_history has no UPDATE/DELETE policy
\echo '2.3 financial_history UPDATE/DELETE policies (expect 0 rows)'
SELECT policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename = 'financial_history'
  AND cmd IN ('UPDATE','DELETE');

\echo ''
\echo '============================================================'
\echo 'PHASE 3 — TRIGGERS'
\echo '============================================================'

-- 3.1 updated_at trigger fires on clients UPDATE
\echo '3.1 updated_at auto-stamp on clients (expect PASS notice)'
DO $$
DECLARE
  v_id UUID;
  v_before TIMESTAMP;
  v_after  TIMESTAMP;
  v_user_id UUID;
BEGIN
  SELECT id INTO v_user_id FROM auth.users LIMIT 1;
  IF v_user_id IS NULL THEN
    RAISE NOTICE 'SKIP 3.1: no rows in auth.users — create a test user first';
    RETURN;
  END IF;

  INSERT INTO clients (user_id, first_name, last_name, phone)
  VALUES (v_user_id, 'TriggerTest', 'UpdatedAt', 'T3ST_PHONE_001')
  RETURNING id INTO v_id;

  SELECT updated_at INTO v_before FROM clients WHERE id = v_id;
  PERFORM pg_sleep(0.1);
  UPDATE clients SET first_name = 'TriggerTestUpdated' WHERE id = v_id;
  SELECT updated_at INTO v_after FROM clients WHERE id = v_id;

  DELETE FROM clients WHERE id = v_id;

  IF v_after > v_before THEN
    RAISE NOTICE 'PASS 3.1: updated_at advanced (before=%, after=%)', v_before, v_after;
  ELSE
    RAISE EXCEPTION 'FAIL 3.1: updated_at did not advance (before=%, after=%)', v_before, v_after;
  END IF;
END $$;

-- 3.2 Installment user_id sync from credit
\echo '3.2 installment.user_id synced from credit (expect PASS notice)'
DO $$
DECLARE
  v_credit_id UUID;
  v_credit_user UUID;
  v_inst_id UUID;
  v_inst_user UUID;
BEGIN
  SELECT id, user_id INTO v_credit_id, v_credit_user FROM credits LIMIT 1;
  IF v_credit_id IS NULL THEN
    RAISE NOTICE 'SKIP 3.2: no rows in credits — insert test data first';
    RETURN;
  END IF;

  INSERT INTO installments (credit_id, period_number, expected_date, expected_value, principal_portion, interest_portion)
  VALUES (v_credit_id, 88888, CURRENT_DATE + 365, 100.00, 80.00, 20.00)
  RETURNING id INTO v_inst_id;

  SELECT user_id INTO v_inst_user FROM installments WHERE id = v_inst_id;
  DELETE FROM installments WHERE id = v_inst_id;

  IF v_inst_user = v_credit_user THEN
    RAISE NOTICE 'PASS 3.2: installment.user_id=% matches credit.user_id', v_inst_user;
  ELSE
    RAISE EXCEPTION 'FAIL 3.2: installment.user_id=% != credit.user_id=%', v_inst_user, v_credit_user;
  END IF;
END $$;

-- 3.3 Payment user_id sync from credit
\echo '3.3 payment.user_id synced from credit (expect PASS notice)'
DO $$
DECLARE
  v_credit_id UUID;
  v_credit_user UUID;
  v_pay_id UUID;
  v_pay_user UUID;
BEGIN
  SELECT id, user_id INTO v_credit_id, v_credit_user FROM credits LIMIT 1;
  IF v_credit_id IS NULL THEN
    RAISE NOTICE 'SKIP 3.3: no rows in credits';
    RETURN;
  END IF;

  INSERT INTO payments (credit_id, amount, payment_date, applied_to, recorded_by)
  VALUES (v_credit_id, 50.00, CURRENT_DATE, '[]'::jsonb, 'run_all_test')
  RETURNING id INTO v_pay_id;

  SELECT user_id INTO v_pay_user FROM payments WHERE id = v_pay_id;
  DELETE FROM payments WHERE id = v_pay_id;

  IF v_pay_user = v_credit_user THEN
    RAISE NOTICE 'PASS 3.3: payment.user_id=% matches credit.user_id', v_pay_user;
  ELSE
    RAISE EXCEPTION 'FAIL 3.3: payment.user_id=% != credit.user_id=%', v_pay_user, v_credit_user;
  END IF;
END $$;

\echo ''
\echo '============================================================'
\echo 'PHASE 4 — FAILURE FORCING'
\echo '============================================================'

-- 4.1 FK violation — bad client_id on credits
\echo '4.1 FK violation: bad client_id (expect error 23503)'
DO $$
BEGIN
  INSERT INTO credits (
    user_id, client_id, initial_capital, pending_capital,
    periodicity, annual_interest_rate, status, start_date
  ) VALUES (
    (SELECT id FROM auth.users LIMIT 1),
    '00000000-0000-0000-0000-000000000000',
    1000.00, 1000.00, 'MONTHLY', 12.00, 'ACTIVE', CURRENT_DATE
  );
  RAISE EXCEPTION 'FAIL 4.1: INSERT should have been blocked by FK';
EXCEPTION
  WHEN foreign_key_violation THEN
    RAISE NOTICE 'PASS 4.1: FK violation caught (SQLSTATE 23503)';
END $$;

-- 4.2 FK violation — bad credit_id on installments
\echo '4.2 FK violation: bad credit_id on installments (expect error 23503)'
DO $$
BEGIN
  INSERT INTO installments (credit_id, period_number, expected_date, expected_value, principal_portion, interest_portion)
  VALUES ('00000000-0000-0000-0000-000000000000', 1, CURRENT_DATE, 100.00, 80.00, 20.00);
  RAISE EXCEPTION 'FAIL 4.2: INSERT should have been blocked by FK';
EXCEPTION
  WHEN foreign_key_violation THEN
    RAISE NOTICE 'PASS 4.2: FK violation caught (SQLSTATE 23503)';
END $$;

-- 4.3 Trigger violation — UPDATE installment locked field
\echo '4.3 Trigger: locked installment field (expect error P0001)'
DO $$
DECLARE v_inst_id UUID;
BEGIN
  SELECT id INTO v_inst_id FROM installments LIMIT 1;
  IF v_inst_id IS NULL THEN
    RAISE NOTICE 'SKIP 4.3: no installments in DB';
    RETURN;
  END IF;

  UPDATE installments SET expected_value = 0.01 WHERE id = v_inst_id;
  RAISE EXCEPTION 'FAIL 4.3: UPDATE should have been blocked by trigger';
EXCEPTION
  WHEN raise_exception THEN
    RAISE NOTICE 'PASS 4.3: Trigger blocked locked field update (SQLSTATE P0001)';
END $$;

-- 4.4 Trigger violation — UPDATE financial_history
\echo '4.4 Trigger: financial_history immutable UPDATE (expect error P0001)'
DO $$
DECLARE v_hist_id UUID;
BEGIN
  SELECT id INTO v_hist_id FROM financial_history LIMIT 1;
  IF v_hist_id IS NULL THEN
    RAISE NOTICE 'SKIP 4.4: no financial_history rows in DB';
    RETURN;
  END IF;

  UPDATE financial_history SET operator_id = 'intruder' WHERE id = v_hist_id;
  RAISE EXCEPTION 'FAIL 4.4: UPDATE should have been blocked by trigger';
EXCEPTION
  WHEN raise_exception THEN
    RAISE NOTICE 'PASS 4.4: Trigger blocked financial_history UPDATE (SQLSTATE P0001)';
END $$;

-- 4.5 Trigger violation — DELETE financial_history
\echo '4.5 Trigger: financial_history immutable DELETE (expect error P0001)'
DO $$
DECLARE v_hist_id UUID;
BEGIN
  SELECT id INTO v_hist_id FROM financial_history LIMIT 1;
  IF v_hist_id IS NULL THEN
    RAISE NOTICE 'SKIP 4.5: no financial_history rows in DB';
    RETURN;
  END IF;

  DELETE FROM financial_history WHERE id = v_hist_id;
  RAISE EXCEPTION 'FAIL 4.5: DELETE should have been blocked by trigger';
EXCEPTION
  WHEN raise_exception THEN
    RAISE NOTICE 'PASS 4.5: Trigger blocked financial_history DELETE (SQLSTATE P0001)';
END $$;

-- 4.6 CHECK violation — invalid periodicity
\echo '4.6 CHECK violation: invalid periodicity (expect error 23514)'
DO $$
BEGIN
  INSERT INTO credits (
    user_id, client_id, initial_capital, pending_capital,
    periodicity, annual_interest_rate, status, start_date
  )
  SELECT user_id, id, 100.00, 100.00, 'INVALID_PERIOD', 5.00, 'ACTIVE', CURRENT_DATE
  FROM clients LIMIT 1;
  RAISE EXCEPTION 'FAIL 4.6: INSERT should have been blocked by CHECK';
EXCEPTION
  WHEN check_violation THEN
    RAISE NOTICE 'PASS 4.6: CHECK violation caught (SQLSTATE 23514)';
  WHEN no_data_found THEN
    RAISE NOTICE 'SKIP 4.6: no clients in DB';
END $$;

-- 4.7 CHECK violation — negative initial_capital
\echo '4.7 CHECK violation: negative initial_capital (expect error 23514)'
DO $$
BEGIN
  INSERT INTO credits (
    user_id, client_id, initial_capital, pending_capital,
    periodicity, annual_interest_rate, status, start_date
  )
  SELECT user_id, id, -500.00, 0.00, 'MONTHLY', 5.00, 'ACTIVE', CURRENT_DATE
  FROM clients LIMIT 1;
  RAISE EXCEPTION 'FAIL 4.7: INSERT should have been blocked by CHECK';
EXCEPTION
  WHEN check_violation THEN
    RAISE NOTICE 'PASS 4.7: CHECK violation caught (SQLSTATE 23514)';
  WHEN no_data_found THEN
    RAISE NOTICE 'SKIP 4.7: no clients in DB';
END $$;

-- 4.8 UNIQUE violation — duplicate (credit_id, period_number)
\echo '4.8 UNIQUE violation: duplicate installment period (expect error 23505)'
DO $$
DECLARE v_credit_id UUID;
BEGIN
  SELECT id INTO v_credit_id FROM credits LIMIT 1;
  IF v_credit_id IS NULL THEN
    RAISE NOTICE 'SKIP 4.8: no credits in DB';
    RETURN;
  END IF;

  INSERT INTO installments (credit_id, period_number, expected_date, expected_value, principal_portion, interest_portion)
  VALUES (v_credit_id, 77777, CURRENT_DATE, 100.00, 80.00, 20.00);

  BEGIN
    INSERT INTO installments (credit_id, period_number, expected_date, expected_value, principal_portion, interest_portion)
    VALUES (v_credit_id, 77777, CURRENT_DATE + 1, 200.00, 160.00, 40.00);
    RAISE EXCEPTION 'FAIL 4.8: second INSERT should have been blocked by UNIQUE';
  EXCEPTION
    WHEN unique_violation THEN
      RAISE NOTICE 'PASS 4.8: UNIQUE violation caught (SQLSTATE 23505)';
  END;

  DELETE FROM installments WHERE credit_id = v_credit_id AND period_number = 77777;
END $$;

\echo ''
\echo '============================================================'
\echo 'PHASE 5 — FUNCTIONS AND TRIGGERS REGISTERED'
\echo '============================================================'

\echo '5.1 Trigger functions exist (expect 7 rows)'
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

\echo '5.2 Triggers registered (expect 10 rows)'
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

\echo ''
\echo '============================================================'
\echo 'run_all.sql complete.'
\echo 'RLS context tests (PHASE 2.4–2.6) require UUIDs — see CHECKLIST.md.'
\echo '============================================================'
