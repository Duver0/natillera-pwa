-- Migration: 003_triggers_and_functions.sql
-- Description: DB-level triggers and helper functions for Natillera PWA
-- Date: 2026-04-23

-- ============================================================
-- FUNCTION: updated_at auto-stamp
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to tables that have updated_at
DROP TRIGGER IF EXISTS set_updated_at_users ON public.users;
CREATE TRIGGER set_updated_at_users
  BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS set_updated_at_clients ON clients;
CREATE TRIGGER set_updated_at_clients
  BEFORE UPDATE ON clients
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS set_updated_at_credits ON credits;
CREATE TRIGGER set_updated_at_credits
  BEFORE UPDATE ON credits
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- FUNCTION: Sync installment user_id from parent credit
-- (Already defined in 001 but reproduced here for clarity)
-- ============================================================
CREATE OR REPLACE FUNCTION sync_installment_user_id()
RETURNS TRIGGER AS $$
BEGIN
  NEW.user_id := (SELECT user_id FROM credits WHERE id = NEW.credit_id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS installment_user_sync ON installments;
CREATE TRIGGER installment_user_sync
  BEFORE INSERT ON installments
  FOR EACH ROW EXECUTE FUNCTION sync_installment_user_id();

-- ============================================================
-- FUNCTION: Sync payment user_id from parent credit
-- ============================================================
CREATE OR REPLACE FUNCTION sync_payment_user_id()
RETURNS TRIGGER AS $$
BEGIN
  NEW.user_id := (SELECT user_id FROM credits WHERE id = NEW.credit_id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS payment_user_sync ON payments;
CREATE TRIGGER payment_user_sync
  BEFORE INSERT ON payments
  FOR EACH ROW EXECUTE FUNCTION sync_payment_user_id();

-- ============================================================
-- FUNCTION: Sync savings user_id from parent client
-- ============================================================
CREATE OR REPLACE FUNCTION sync_savings_user_id()
RETURNS TRIGGER AS $$
BEGIN
  NEW.user_id := (SELECT user_id FROM clients WHERE id = NEW.client_id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS savings_user_sync ON savings;
CREATE TRIGGER savings_user_sync
  BEFORE INSERT ON savings
  FOR EACH ROW EXECUTE FUNCTION sync_savings_user_id();

DROP TRIGGER IF EXISTS savings_liquidations_user_sync ON savings_liquidations;
CREATE TRIGGER savings_liquidations_user_sync
  BEFORE INSERT ON savings_liquidations
  FOR EACH ROW EXECUTE FUNCTION sync_savings_user_id();

-- ============================================================
-- FUNCTION: Prevent UPDATE on financial_history (immutable audit log)
-- ============================================================
CREATE OR REPLACE FUNCTION prevent_history_update()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'financial_history is immutable. Updates are not allowed.';
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS financial_history_immutable ON financial_history;
CREATE TRIGGER financial_history_immutable
  BEFORE UPDATE OR DELETE ON financial_history
  FOR EACH ROW EXECUTE FUNCTION prevent_history_update();

-- ============================================================
-- FUNCTION: Prevent retroactive changes to installment locked fields
-- ============================================================
CREATE OR REPLACE FUNCTION protect_installment_locked_fields()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.expected_value IS DISTINCT FROM NEW.expected_value THEN
    RAISE EXCEPTION 'installment.expected_value is immutable after creation';
  END IF;
  IF OLD.principal_portion IS DISTINCT FROM NEW.principal_portion THEN
    RAISE EXCEPTION 'installment.principal_portion is immutable after creation';
  END IF;
  IF OLD.interest_portion IS DISTINCT FROM NEW.interest_portion THEN
    RAISE EXCEPTION 'installment.interest_portion is immutable after creation';
  END IF;
  IF OLD.period_number IS DISTINCT FROM NEW.period_number THEN
    RAISE EXCEPTION 'installment.period_number is immutable after creation';
  END IF;
  IF OLD.expected_date IS DISTINCT FROM NEW.expected_date THEN
    RAISE EXCEPTION 'installment.expected_date is immutable after creation';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS installment_locked_fields ON installments;
CREATE TRIGGER installment_locked_fields
  BEFORE UPDATE ON installments
  FOR EACH ROW EXECUTE FUNCTION protect_installment_locked_fields();

-- ============================================================
-- FUNCTION: Auto-create public.users row when auth.users is created
-- (Supabase hook — register in Supabase dashboard or via DB trigger)
-- ============================================================
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email, created_at, updated_at)
  VALUES (NEW.id, NEW.email, NOW(), NOW())
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();
