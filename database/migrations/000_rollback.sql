-- Rollback: 000_rollback.sql
-- Description: Full teardown of all Natillera PWA tables (use in dev/test only)
-- WARNING: Destroys all data. Do NOT run in production.
-- Date: 2026-04-23

-- Drop triggers first
DROP TRIGGER IF EXISTS financial_history_immutable ON financial_history;
DROP TRIGGER IF EXISTS installment_locked_fields ON installments;
DROP TRIGGER IF EXISTS installment_user_sync ON installments;
DROP TRIGGER IF EXISTS payment_user_sync ON payments;
DROP TRIGGER IF EXISTS savings_user_sync ON savings;
DROP TRIGGER IF EXISTS savings_liquidations_user_sync ON savings_liquidations;
DROP TRIGGER IF EXISTS set_updated_at_users ON public.users;
DROP TRIGGER IF EXISTS set_updated_at_clients ON clients;
DROP TRIGGER IF EXISTS set_updated_at_credits ON credits;
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Drop functions
DROP FUNCTION IF EXISTS prevent_history_update();
DROP FUNCTION IF EXISTS protect_installment_locked_fields();
DROP FUNCTION IF EXISTS sync_installment_user_id();
DROP FUNCTION IF EXISTS sync_payment_user_id();
DROP FUNCTION IF EXISTS sync_savings_user_id();
DROP FUNCTION IF EXISTS set_updated_at();
DROP FUNCTION IF EXISTS handle_new_user();

-- Drop tables in FK-safe order
DROP TABLE IF EXISTS financial_history CASCADE;
DROP TABLE IF EXISTS savings_liquidations CASCADE;
DROP TABLE IF EXISTS savings CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS installments CASCADE;
DROP TABLE IF EXISTS credits CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;
