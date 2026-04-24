-- Migration: 001_initial_schema.sql
-- Description: Create all base tables for Natillera PWA (SPEC-001 v2.0)
-- Auth: Supabase Auth (auth.users managed by Supabase)
-- Date: 2026-04-23

-- ============================================================
-- EXTENSION
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TABLE: public.users (extends auth.users)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL UNIQUE,
  email_verified BOOLEAN DEFAULT FALSE,
  phone VARCHAR(20),
  first_name VARCHAR(255),
  last_name VARCHAR(255),
  last_login_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON public.users(created_at);

-- ============================================================
-- TABLE: clients
-- ============================================================
CREATE TABLE IF NOT EXISTS clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  first_name VARCHAR(255) NOT NULL,
  last_name VARCHAR(255) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  document_id VARCHAR(50),
  address TEXT,
  notes TEXT CHECK (length(notes) <= 500),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP,
  CONSTRAINT clients_user_phone_unique UNIQUE(user_id, phone),
  CONSTRAINT clients_user_document_unique UNIQUE(user_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_clients_user ON clients(user_id);
CREATE INDEX IF NOT EXISTS idx_clients_deleted ON clients(deleted_at);

-- ============================================================
-- TABLE: credits
-- ============================================================
CREATE TABLE IF NOT EXISTS credits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  initial_capital DECIMAL(12,2) NOT NULL CHECK (initial_capital > 0),
  pending_capital DECIMAL(12,2) NOT NULL CHECK (pending_capital >= 0),
  version INT DEFAULT 1,
  periodicity VARCHAR(20) NOT NULL CHECK (periodicity IN ('DAILY', 'WEEKLY', 'BIWEEKLY', 'MONTHLY')),
  annual_interest_rate DECIMAL(5,2) NOT NULL CHECK (annual_interest_rate >= 0),
  status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'CLOSED', 'SUSPENDED')) DEFAULT 'ACTIVE',
  start_date DATE NOT NULL,
  closed_date DATE,
  next_period_date DATE,
  mora BOOLEAN DEFAULT FALSE,
  mora_since DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_credits_user ON credits(user_id);
CREATE INDEX IF NOT EXISTS idx_credits_client ON credits(client_id);
CREATE INDEX IF NOT EXISTS idx_credits_status ON credits(status);
CREATE INDEX IF NOT EXISTS idx_credits_mora ON credits(mora);

-- ============================================================
-- TABLE: installments
-- ============================================================
CREATE TABLE IF NOT EXISTS installments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  credit_id UUID NOT NULL REFERENCES credits(id) ON DELETE CASCADE,
  period_number INT NOT NULL,
  expected_date DATE NOT NULL,
  expected_value DECIMAL(12,2) NOT NULL CHECK (expected_value > 0),
  principal_portion DECIMAL(12,2) NOT NULL CHECK (principal_portion > 0),
  interest_portion DECIMAL(12,2) NOT NULL CHECK (interest_portion >= 0),
  paid_value DECIMAL(12,2) DEFAULT 0 CHECK (paid_value >= 0),
  is_overdue BOOLEAN DEFAULT FALSE,
  status VARCHAR(20) NOT NULL CHECK (status IN ('UPCOMING', 'PARTIALLY_PAID', 'PAID', 'SUSPENDED')) DEFAULT 'UPCOMING',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  paid_at TIMESTAMP,
  UNIQUE(credit_id, period_number)
);

CREATE INDEX IF NOT EXISTS idx_installments_user ON installments(user_id);
CREATE INDEX IF NOT EXISTS idx_installments_credit ON installments(credit_id);
CREATE INDEX IF NOT EXISTS idx_installments_expected_date ON installments(expected_date);
CREATE INDEX IF NOT EXISTS idx_installments_is_overdue ON installments(is_overdue) WHERE is_overdue = TRUE;

-- Trigger: sync user_id from credit to installment on insert
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
-- TABLE: payments
-- ============================================================
CREATE TABLE IF NOT EXISTS payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  credit_id UUID NOT NULL REFERENCES credits(id) ON DELETE CASCADE,
  amount DECIMAL(12,2) NOT NULL CHECK (amount > 0),
  payment_date DATE NOT NULL,
  applied_to JSONB NOT NULL,
  notes TEXT,
  recorded_by VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_credit ON payments(credit_id);
CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);

-- ============================================================
-- TABLE: savings
-- ============================================================
CREATE TABLE IF NOT EXISTS savings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  contribution_amount DECIMAL(12,2) NOT NULL CHECK (contribution_amount > 0),
  contribution_date DATE NOT NULL,
  status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'LIQUIDATED')) DEFAULT 'ACTIVE',
  liquidated_at DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_savings_user ON savings(user_id);
CREATE INDEX IF NOT EXISTS idx_savings_client ON savings(client_id);
CREATE INDEX IF NOT EXISTS idx_savings_status ON savings(status);

-- ============================================================
-- TABLE: savings_liquidations
-- ============================================================
CREATE TABLE IF NOT EXISTS savings_liquidations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  total_contributions DECIMAL(12,2) NOT NULL CHECK (total_contributions > 0),
  interest_earned DECIMAL(12,2) NOT NULL CHECK (interest_earned >= 0),
  total_delivered DECIMAL(12,2) NOT NULL CHECK (total_delivered > 0),
  interest_rate DECIMAL(5,2) NOT NULL CHECK (interest_rate >= 0),
  liquidation_date DATE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_savings_liquidations_user ON savings_liquidations(user_id);
CREATE INDEX IF NOT EXISTS idx_savings_liquidations_client ON savings_liquidations(client_id);

-- ============================================================
-- TABLE: financial_history (append-only, immutable audit log)
-- ============================================================
CREATE TABLE IF NOT EXISTS financial_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
    'CREDIT_CREATED', 'CREDIT_CLOSED', 'CREDIT_SUSPENDED',
    'INSTALLMENT_GENERATED',
    'PAYMENT_RECORDED',
    'SAVINGS_CONTRIBUTION', 'SAVINGS_LIQUIDATION',
    'CLIENT_CREATED', 'CLIENT_DELETED'
  )),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  credit_id UUID REFERENCES credits(id) ON DELETE SET NULL,
  amount DECIMAL(12,2),
  description TEXT NOT NULL,
  metadata JSONB,
  operator_id VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_financial_history_user ON financial_history(user_id);
CREATE INDEX IF NOT EXISTS idx_financial_history_client ON financial_history(client_id);
CREATE INDEX IF NOT EXISTS idx_financial_history_event_type ON financial_history(event_type);
CREATE INDEX IF NOT EXISTS idx_financial_history_created_at ON financial_history(created_at);
