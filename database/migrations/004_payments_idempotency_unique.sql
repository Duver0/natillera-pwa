-- Migration: 004_payments_idempotency_unique.sql
-- Description: Add idempotency_key column + unique index on payments table (CF-5 fix)
-- Date: 2026-04-24
-- Author: backend-developer (P0 remediation)
-- Depends on: 001_initial_schema.sql, 003_payment_atomic_rpc.sql
-- NOTE: Apply manually — live Supabase PENDING-HUMAN. Do NOT run supabase start.

-- ============================================================
-- Step 1: Add column if missing (idempotent DDL)
-- ============================================================
ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

-- ============================================================
-- Step 2: Unique index — scope: (credit_id, idempotency_key)
-- Partial: only when idempotency_key IS NOT NULL
-- This allows multiple payments without a key (NULL != NULL in UNIQUE)
-- ============================================================
CREATE UNIQUE INDEX IF NOT EXISTS payments_idempotency_key_unique
    ON payments(credit_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- ============================================================
-- Step 3: Index for fast lookup in RPC idempotency check
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_payments_credit_idempotency
    ON payments(credit_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

COMMENT ON COLUMN payments.idempotency_key IS
    'Optional client-supplied key to prevent duplicate payment on network retry. '
    'Uniqueness scoped to (credit_id, idempotency_key). '
    'RPC returns cached result (HTTP 200) when key already exists — no duplicate write. '
    'Added in P0 remediation 2026-04-24 (CF-5).';
