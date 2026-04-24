-- Migration: 002_rls_policies.sql
-- Description: Enable Row-Level Security and create all RLS policies (SPEC-002 v1.0)
-- All tables scoped to authenticated Supabase user via auth.uid()
-- Date: 2026-04-23

-- ============================================================
-- ENABLE RLS ON ALL TABLES
-- ============================================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE installments ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings_liquidations ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_history ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- POLICIES: public.users
-- ============================================================
DROP POLICY IF EXISTS "users_view_own_profile" ON public.users;
CREATE POLICY "users_view_own_profile" ON public.users
  FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "users_insert_own_profile" ON public.users;
CREATE POLICY "users_insert_own_profile" ON public.users
  FOR INSERT WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "users_update_own_profile" ON public.users;
CREATE POLICY "users_update_own_profile" ON public.users
  FOR UPDATE USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- ============================================================
-- POLICIES: clients
-- ============================================================
DROP POLICY IF EXISTS "clients_select_user_owned" ON clients;
CREATE POLICY "clients_select_user_owned" ON clients
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "clients_insert_user_owned" ON clients;
CREATE POLICY "clients_insert_user_owned" ON clients
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "clients_update_user_owned" ON clients;
CREATE POLICY "clients_update_user_owned" ON clients
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "clients_delete_user_owned" ON clients;
CREATE POLICY "clients_delete_user_owned" ON clients
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- POLICIES: credits
-- ============================================================
DROP POLICY IF EXISTS "credits_select_user_owned" ON credits;
CREATE POLICY "credits_select_user_owned" ON credits
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "credits_insert_user_owned" ON credits;
CREATE POLICY "credits_insert_user_owned" ON credits
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "credits_update_user_owned" ON credits;
CREATE POLICY "credits_update_user_owned" ON credits
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "credits_delete_user_owned" ON credits;
CREATE POLICY "credits_delete_user_owned" ON credits
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- POLICIES: installments
-- ============================================================
DROP POLICY IF EXISTS "installments_select_user_owned" ON installments;
CREATE POLICY "installments_select_user_owned" ON installments
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "installments_insert_user_owned" ON installments;
CREATE POLICY "installments_insert_user_owned" ON installments
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "installments_update_user_owned" ON installments;
CREATE POLICY "installments_update_user_owned" ON installments
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "installments_delete_user_owned" ON installments;
CREATE POLICY "installments_delete_user_owned" ON installments
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- POLICIES: payments
-- ============================================================
DROP POLICY IF EXISTS "payments_select_user_owned" ON payments;
CREATE POLICY "payments_select_user_owned" ON payments
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "payments_insert_user_owned" ON payments;
CREATE POLICY "payments_insert_user_owned" ON payments
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "payments_update_user_owned" ON payments;
CREATE POLICY "payments_update_user_owned" ON payments
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "payments_delete_user_owned" ON payments;
CREATE POLICY "payments_delete_user_owned" ON payments
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- POLICIES: savings
-- ============================================================
DROP POLICY IF EXISTS "savings_select_user_owned" ON savings;
CREATE POLICY "savings_select_user_owned" ON savings
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "savings_insert_user_owned" ON savings;
CREATE POLICY "savings_insert_user_owned" ON savings
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "savings_update_user_owned" ON savings;
CREATE POLICY "savings_update_user_owned" ON savings
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "savings_delete_user_owned" ON savings;
CREATE POLICY "savings_delete_user_owned" ON savings
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- POLICIES: savings_liquidations
-- ============================================================
DROP POLICY IF EXISTS "savings_liquidations_select_user_owned" ON savings_liquidations;
CREATE POLICY "savings_liquidations_select_user_owned" ON savings_liquidations
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "savings_liquidations_insert_user_owned" ON savings_liquidations;
CREATE POLICY "savings_liquidations_insert_user_owned" ON savings_liquidations
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "savings_liquidations_update_user_owned" ON savings_liquidations;
CREATE POLICY "savings_liquidations_update_user_owned" ON savings_liquidations
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "savings_liquidations_delete_user_owned" ON savings_liquidations;
CREATE POLICY "savings_liquidations_delete_user_owned" ON savings_liquidations
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- POLICIES: financial_history
-- ============================================================
DROP POLICY IF EXISTS "financial_history_select_user_owned" ON financial_history;
CREATE POLICY "financial_history_select_user_owned" ON financial_history
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "financial_history_insert_user_owned" ON financial_history;
CREATE POLICY "financial_history_insert_user_owned" ON financial_history
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- financial_history is append-only: no UPDATE or DELETE policies
-- Attempting UPDATE or DELETE will fail with RLS violation (no policy = deny)

-- ============================================================
-- VERIFICATION QUERY
-- ============================================================
-- Run this to confirm RLS is active on all tables:
-- SELECT schemaname, tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
--   AND tablename IN (
--     'users', 'clients', 'credits', 'installments',
--     'payments', 'savings', 'savings_liquidations', 'financial_history'
--   );
