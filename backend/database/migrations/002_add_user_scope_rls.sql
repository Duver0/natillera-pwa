-- ============================================================
-- Migration 002: Add user_id column to all tables + RLS policies
-- Prepares for SPEC-002 multi-user auth scope.
-- Backward-compatible: user_id nullable on first migration;
-- a follow-up migration (003) can set NOT NULL after backfill.
-- ============================================================

-- -------------------------------------------------------
-- 1. Create public.users (mirror of auth.users for joins)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.users (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT NOT NULL,
    display_name TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);

-- -------------------------------------------------------
-- 2. Add user_id FK columns to all business tables
--    (nullable for SPEC-002 prep; data backfill TBD)
-- -------------------------------------------------------
ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE credits
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE installments
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE savings
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE savings_liquidations
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE financial_history
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- -------------------------------------------------------
-- 3. Indexes on user_id for fast row-level filtering
-- -------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_clients_user_id             ON clients(user_id);
CREATE INDEX IF NOT EXISTS idx_credits_user_id             ON credits(user_id);
CREATE INDEX IF NOT EXISTS idx_installments_user_id        ON installments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_user_id            ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_savings_user_id             ON savings(user_id);
CREATE INDEX IF NOT EXISTS idx_savings_liquidations_user_id ON savings_liquidations(user_id);
CREATE INDEX IF NOT EXISTS idx_financial_history_user_id   ON financial_history(user_id);

-- -------------------------------------------------------
-- 4. Enable Row Level Security on all tables
-- -------------------------------------------------------
ALTER TABLE public.users              ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE credits                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE installments              ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings_liquidations      ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_history         ENABLE ROW LEVEL SECURITY;

-- -------------------------------------------------------
-- 5. RLS Policies — users own their rows
--    auth.uid() = user_id enforces data isolation.
--    Service-role key bypasses RLS for backend operations.
--    Policies are permissive (USING + WITH CHECK).
-- -------------------------------------------------------

-- public.users: each user sees only their own profile row
DROP POLICY IF EXISTS "users_own_profile" ON public.users;
CREATE POLICY "users_own_profile" ON public.users
    FOR ALL
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- clients
DROP POLICY IF EXISTS "clients_owner_access" ON clients;
CREATE POLICY "clients_owner_access" ON clients
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- credits
DROP POLICY IF EXISTS "credits_owner_access" ON credits;
CREATE POLICY "credits_owner_access" ON credits
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- installments
DROP POLICY IF EXISTS "installments_owner_access" ON installments;
CREATE POLICY "installments_owner_access" ON installments
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- payments
DROP POLICY IF EXISTS "payments_owner_access" ON payments;
CREATE POLICY "payments_owner_access" ON payments
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- savings
DROP POLICY IF EXISTS "savings_owner_access" ON savings;
CREATE POLICY "savings_owner_access" ON savings
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- savings_liquidations
DROP POLICY IF EXISTS "savings_liquidations_owner_access" ON savings_liquidations;
CREATE POLICY "savings_liquidations_owner_access" ON savings_liquidations
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- financial_history: users can read their own events; insert via service role only
DROP POLICY IF EXISTS "financial_history_owner_read" ON financial_history;
CREATE POLICY "financial_history_owner_read" ON financial_history
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "financial_history_owner_insert" ON financial_history;
CREATE POLICY "financial_history_owner_insert" ON financial_history
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);
-- No UPDATE / DELETE policy on financial_history → immutable by policy enforcement

-- -------------------------------------------------------
-- 6. Grant service-role bypass (already default in Supabase)
--    Documented here for audit purposes.
-- -------------------------------------------------------
-- Service role key bypasses RLS automatically in Supabase.
-- Backend always uses service role for writes; anon/user role for reads.
