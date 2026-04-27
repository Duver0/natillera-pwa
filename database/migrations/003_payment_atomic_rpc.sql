-- Migration: 003_payment_atomic_rpc.sql
-- Description: Atomic payment processing via PostgreSQL RPC (resolves CF-1, CF-2, CF-3, CF-4, CF-5)
-- Fixes: CF-1 (no atomicity), CF-2 (dirty writes on 409), CF-3 (allocation order), CF-4 (mora_since),
--        CF-5 (idempotency dead code)
-- Date: 2026-04-24
-- Author: backend-developer (P0 remediation)
-- NOTE: Apply manually — live Supabase PENDING-HUMAN. Do NOT run supabase start.

-- ============================================================
-- NAMED EXCEPTION CODES
-- ============================================================
-- VersionConflict  → SQLSTATE P0001 / message 'VersionConflict'
-- CreditClosed     → SQLSTATE P0002 / message 'CreditClosed'
-- AmountInvalid    → SQLSTATE P0003 / message 'AmountInvalid'
-- CreditNotFound   → SQLSTATE P0004 / message 'CreditNotFound'

CREATE OR REPLACE FUNCTION process_payment_atomic(
    p_credit_id      UUID,
    p_amount         NUMERIC(12,2),
    p_operator_id    TEXT,
    p_idempotency_key TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_credit                 RECORD;
    v_expected_version       INTEGER;
    v_installments           RECORD;
    v_payment_id             UUID;
    v_existing_payment       RECORD;

    -- 3-pool aggregates (all NUMERIC to avoid float)
    v_pool_overdue_interest  NUMERIC(12,2) := 0;
    v_pool_overdue_principal NUMERIC(12,2) := 0;
    v_pool_future_principal  NUMERIC(12,2) := 0;

    v_remaining              NUMERIC(12,2);
    v_applied_interest       NUMERIC(12,2);
    v_applied_principal      NUMERIC(12,2);
    v_applied_future         NUMERIC(12,2);

    v_total_principal        NUMERIC(12,2) := 0;
    v_new_pending_capital    NUMERIC(12,2);
    v_mora_after             BOOLEAN;
    v_mora_since_after       DATE;
    v_new_credit_status      TEXT;
    v_new_version            INTEGER;
    v_today                  DATE := CURRENT_DATE;

    v_applied_to             JSON;
    v_applied_entries        JSONB := '[]'::JSONB;
    v_credit_snapshot        JSON;
    v_result                 JSON;
BEGIN
    -- ----------------------------------------------------------------
    -- GUARD: amount must be positive
    -- ----------------------------------------------------------------
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'AmountInvalid' USING ERRCODE = 'P0003';
    END IF;

    -- ----------------------------------------------------------------
    -- STEP 1: Row-lock credit to prevent concurrent payment races
    -- ----------------------------------------------------------------
    SELECT *
    INTO v_credit
    FROM credits
    WHERE id = p_credit_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'CreditNotFound' USING ERRCODE = 'P0004';
    END IF;

    IF v_credit.status != 'ACTIVE' THEN
        RAISE EXCEPTION 'CreditClosed' USING ERRCODE = 'P0002';
    END IF;

    v_expected_version := v_credit.version;

    -- ----------------------------------------------------------------
    -- STEP 2: Idempotency check — return cached result, no reprocessing
    -- ----------------------------------------------------------------
    IF p_idempotency_key IS NOT NULL THEN
        SELECT p.*
        INTO v_existing_payment
        FROM payments p
        WHERE p.credit_id = p_credit_id
          AND p.idempotency_key = p_idempotency_key
        LIMIT 1;

        IF FOUND THEN
            -- Return cached result: rebuild JSON from existing payment
            RETURN json_build_object(
                'idempotent',        TRUE,
                'payment_id',        v_existing_payment.id,
                'credit_id',         p_credit_id,
                'total_amount',      v_existing_payment.amount::TEXT,
                'applied_to',        v_existing_payment.applied_to,
                'updated_credit_snapshot', json_build_object(
                    'pending_capital', v_credit.pending_capital::TEXT,
                    'mora',            v_credit.mora,
                    'version',         v_credit.version
                )
            );
        END IF;
    END IF;

    -- ----------------------------------------------------------------
    -- STEP 3: Fetch unpaid installments ordered by expected_date ASC
    -- ----------------------------------------------------------------

    -- ----------------------------------------------------------------
    -- STEP 4: Build 3 GLOBAL POOLS across all installments
    -- Pool 1: ALL overdue interest owed
    -- Pool 2: ALL overdue principal owed
    -- Pool 3: ALL future principal owed
    -- ----------------------------------------------------------------
    SELECT
        COALESCE(SUM(
            CASE WHEN expected_date < v_today AND status != 'PAID'
            THEN GREATEST(
                ROUND(interest_portion - LEAST(paid_value, interest_portion), 2),
                0
            )
            ELSE 0 END
        ), 0),
        COALESCE(SUM(
            CASE WHEN expected_date < v_today AND status != 'PAID'
            THEN GREATEST(
                ROUND(expected_value - GREATEST(paid_value, interest_portion), 2),
                0
            )
            ELSE 0 END
        ), 0),
        COALESCE(SUM(
            CASE WHEN expected_date >= v_today AND status NOT IN ('PAID')
            THEN GREATEST(
                ROUND(expected_value - paid_value, 2),
                0
            )
            ELSE 0 END
        ), 0)
    INTO
        v_pool_overdue_interest,
        v_pool_overdue_principal,
        v_pool_future_principal
    FROM installments
    WHERE credit_id = p_credit_id
      AND status IN ('UPCOMING', 'PARTIALLY_PAID');

    -- ----------------------------------------------------------------
    -- STEP 5: Consume payment in strict global order
    -- ALL overdue_interest → ALL overdue_principal → future_principal
    -- ----------------------------------------------------------------
    v_remaining := p_amount;

    -- Consume pool 1: overdue interest
    v_applied_interest := LEAST(v_remaining, v_pool_overdue_interest);
    v_remaining := v_remaining - v_applied_interest;

    -- Consume pool 2: overdue principal
    v_applied_principal := LEAST(v_remaining, v_pool_overdue_principal);
    v_remaining := v_remaining - v_applied_principal;

    -- Consume pool 3: future principal
    v_applied_future := LEAST(v_remaining, v_pool_future_principal);
    v_remaining := v_remaining - v_applied_future;

    v_total_principal := v_applied_principal + v_applied_future;

    -- ----------------------------------------------------------------
    -- STEP 6: UPDATE installments — distribute pools per-installment
    -- Allocation order within each pool: ASC expected_date (FIFO)
    -- LOCKED fields (principal_portion, interest_portion, expected_value, expected_date) UNTOUCHED.
    -- ----------------------------------------------------------------
    DECLARE
        v_pool1_left  NUMERIC(12,2) := v_applied_interest;
        v_pool2_left  NUMERIC(12,2) := v_applied_principal;
        v_pool3_left  NUMERIC(12,2) := v_applied_future;
        v_inst        RECORD;
        v_inst_new_paid NUMERIC(12,2);
        v_inst_new_status TEXT;
        v_inst_paid_at  DATE;
        v_inst_is_overdue BOOLEAN;
        v_inst_interest_owed NUMERIC(12,2);
        v_inst_principal_owed NUMERIC(12,2);
        v_inst_future_owed NUMERIC(12,2);
        v_take_interest  NUMERIC(12,2);
        v_take_principal NUMERIC(12,2);
        v_take_future    NUMERIC(12,2);
        v_entry          JSONB;
    BEGIN
        FOR v_inst IN
            SELECT *
            FROM installments
            WHERE credit_id = p_credit_id
              AND status IN ('UPCOMING', 'PARTIALLY_PAID')
            ORDER BY expected_date ASC
        LOOP
            v_inst_new_paid := v_inst.paid_value;
            v_take_interest  := 0;
            v_take_principal := 0;
            v_take_future    := 0;

            IF v_inst.expected_date < v_today AND v_inst.status != 'PAID' THEN
                -- Overdue installment: apply from pool1 then pool2

                -- Interest portion still owed by this installment
                v_inst_interest_owed := GREATEST(
                    ROUND(v_inst.interest_portion - LEAST(v_inst.paid_value, v_inst.interest_portion), 2),
                    0
                );
                -- Principal portion still owed by this installment
                v_inst_principal_owed := GREATEST(
                    ROUND(v_inst.expected_value - GREATEST(v_inst.paid_value, v_inst.interest_portion), 2),
                    0
                );

                -- Take from pool 1 (overdue interest)
                IF v_pool1_left > 0 AND v_inst_interest_owed > 0 THEN
                    v_take_interest := LEAST(v_pool1_left, v_inst_interest_owed);
                    v_pool1_left    := v_pool1_left - v_take_interest;
                    v_inst_new_paid := v_inst_new_paid + v_take_interest;
                    v_entry := jsonb_build_object(
                        'installment_id', v_inst.id,
                        'type', 'OVERDUE_INTEREST',
                        'amount', v_take_interest::TEXT
                    );
                    v_applied_entries := v_applied_entries || v_entry;
                END IF;

                -- Take from pool 2 (overdue principal)
                IF v_pool2_left > 0 AND v_inst_principal_owed > 0 THEN
                    v_take_principal := LEAST(v_pool2_left, v_inst_principal_owed);
                    v_pool2_left     := v_pool2_left - v_take_principal;
                    v_inst_new_paid  := v_inst_new_paid + v_take_principal;
                    v_entry := jsonb_build_object(
                        'installment_id', v_inst.id,
                        'type', 'OVERDUE_PRINCIPAL',
                        'amount', v_take_principal::TEXT
                    );
                    v_applied_entries := v_applied_entries || v_entry;
                END IF;

            ELSE
                -- Future installment: apply from pool 3 only
                v_inst_future_owed := GREATEST(
                    ROUND(v_inst.expected_value - v_inst.paid_value, 2),
                    0
                );

                IF v_pool3_left > 0 AND v_inst_future_owed > 0 THEN
                    v_take_future   := LEAST(v_pool3_left, v_inst_future_owed);
                    v_pool3_left    := v_pool3_left - v_take_future;
                    v_inst_new_paid := v_inst_new_paid + v_take_future;
                    v_entry := jsonb_build_object(
                        'installment_id', v_inst.id,
                        'type', 'FUTURE_PRINCIPAL',
                        'amount', v_take_future::TEXT
                    );
                    v_applied_entries := v_applied_entries || v_entry;
                END IF;
            END IF;

            -- Determine new status (only write mutable fields)
            IF v_inst_new_paid >= v_inst.expected_value THEN
                v_inst_new_status  := 'PAID';
                v_inst_paid_at     := v_today;
                v_inst_is_overdue  := FALSE;
            ELSIF v_inst_new_paid > 0 THEN
                v_inst_new_status  := 'PARTIALLY_PAID';
                v_inst_paid_at     := NULL;
                v_inst_is_overdue  := (v_inst.expected_date < v_today);
            ELSE
                v_inst_new_status  := v_inst.status;
                v_inst_paid_at     := NULL;
                v_inst_is_overdue  := v_inst.is_overdue;
            END IF;

            -- Only write if something changed
            IF v_inst_new_paid != v_inst.paid_value OR v_inst_new_status != v_inst.status THEN
                UPDATE installments
                SET
                    paid_value = ROUND(v_inst_new_paid, 2),
                    status     = v_inst_new_status,
                    paid_at    = v_inst_paid_at,
                    is_overdue = v_inst_is_overdue
                WHERE id = v_inst.id;
                -- LOCKED fields NOT included: principal_portion, interest_portion,
                --                              expected_value, expected_date
            END IF;

            -- Exit early if all pools exhausted
            EXIT WHEN v_pool1_left <= 0 AND v_pool2_left <= 0 AND v_pool3_left <= 0;
        END LOOP;
    END;

    -- ----------------------------------------------------------------
    -- STEP 7: Compute new credit state
    -- ----------------------------------------------------------------
    v_new_pending_capital := GREATEST(
        ROUND(v_credit.pending_capital - v_total_principal, 2),
        0
    );

    -- Handle overpayment: excess beyond installments → reduce capital further
    IF v_remaining > 0 AND v_new_pending_capital > 0 THEN
        v_new_pending_capital := GREATEST(
            ROUND(v_new_pending_capital - LEAST(v_remaining, v_new_pending_capital), 2),
            0
        );
    END IF;

    -- Auto-close only when capital reaches zero AND all installments paid
    IF v_new_pending_capital <= 0 AND NOT EXISTS (
        SELECT 1 FROM installments
        WHERE credit_id = p_credit_id
          AND status NOT IN ('PAID', 'SUSPENDED')
    ) THEN
        v_new_credit_status := 'CLOSED';
    ELSE
        v_new_credit_status := v_credit.status;
    END IF;

    -- ----------------------------------------------------------------
    -- STEP 4 (mora): Recompute mora AFTER allocation
    -- mora_since = MIN(expected_date) of remaining overdue installments
    -- CF-4 fix: set mora_since on first activation (not just preserve)
    -- ----------------------------------------------------------------
    SELECT
        (COUNT(*) > 0),
        MIN(expected_date)
    INTO
        v_mora_after,
        v_mora_since_after
    FROM installments
    WHERE credit_id = p_credit_id
      AND expected_date < v_today
      AND status NOT IN ('PAID', 'SUSPENDED');

    IF NOT v_mora_after THEN
        v_mora_since_after := NULL;
    END IF;
    -- If mora_after AND mora_since_after IS NOT NULL → that IS the correct earliest date
    -- (covers both false→true activation and continued mora keeping earliest)

    -- ----------------------------------------------------------------
    -- STEP 7b: UPDATE credits with optimistic lock
    -- ----------------------------------------------------------------
    v_new_version := v_expected_version + 1;

    UPDATE credits
    SET
        pending_capital = v_new_pending_capital,
        mora            = v_mora_after,
        mora_since      = v_mora_since_after,
        status          = v_new_credit_status,
        version         = v_new_version,
        updated_at      = NOW()
    WHERE id      = p_credit_id
      AND version = v_expected_version;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'VersionConflict' USING ERRCODE = 'P0001';
    END IF;

    -- ----------------------------------------------------------------
    -- STEP 8: INSERT payment record (with idempotency_key)
    -- ----------------------------------------------------------------
    INSERT INTO payments (
        id,
        user_id,
        credit_id,
        amount,
        payment_date,
        applied_to,
        notes,
        recorded_by,
        idempotency_key,
        created_at
    ) VALUES (
        gen_random_uuid(),
        v_credit.user_id,
        p_credit_id,
        p_amount,
        v_today,
        v_applied_entries,
        NULL,  -- notes not passed in RPC (optional extension)
        p_operator_id,
        p_idempotency_key,
        NOW()
    )
    RETURNING id INTO v_payment_id;

    -- ----------------------------------------------------------------
    -- STEP 9: INSERT financial_history audit event
    -- ----------------------------------------------------------------
    INSERT INTO financial_history (
        id,
        user_id,
        event_type,
        client_id,
        credit_id,
        amount,
        description,
        metadata,
        operator_id,
        created_at
    ) VALUES (
        gen_random_uuid(),
        v_credit.user_id,
        'PAYMENT_RECORDED',
        v_credit.client_id,
        p_credit_id,
        p_amount,
        'Payment of ' || p_amount::TEXT || ' processed',
        jsonb_build_object(
            'payment_id',   v_payment_id,
            'total_amount', p_amount::TEXT,
            'applied_to',   v_applied_entries
        ),
        p_operator_id,
        NOW()
    );

    -- ----------------------------------------------------------------
    -- STEP 10: RETURN JSON breakdown
    -- ----------------------------------------------------------------
    v_result := json_build_object(
        'idempotent',   FALSE,
        'payment_id',   v_payment_id,
        'credit_id',    p_credit_id,
        'total_amount', p_amount::TEXT,
        'applied_to',   v_applied_entries,
        'updated_credit_snapshot', json_build_object(
            'pending_capital', v_new_pending_capital::TEXT,
            'mora',            v_mora_after,
            'mora_since',      v_mora_since_after,
            'version',         v_new_version,
            'status',          v_new_credit_status
        )
    );

    RETURN v_result;

EXCEPTION
    WHEN SQLSTATE 'P0001' THEN RAISE;  -- VersionConflict — re-raise
    WHEN SQLSTATE 'P0002' THEN RAISE;  -- CreditClosed — re-raise
    WHEN SQLSTATE 'P0003' THEN RAISE;  -- AmountInvalid — re-raise
    WHEN SQLSTATE 'P0004' THEN RAISE;  -- CreditNotFound — re-raise
    -- All other exceptions propagate and trigger automatic rollback
END;
$$;

-- Grant execute to authenticated role (Supabase pattern)
GRANT EXECUTE ON FUNCTION process_payment_atomic(UUID, NUMERIC, TEXT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION process_payment_atomic(UUID, NUMERIC, TEXT, TEXT) TO service_role;

COMMENT ON FUNCTION process_payment_atomic IS
    'P0 remediation 2026-04-24. Resolves CF-1 (atomicity), CF-2 (dirty writes), '
    'CF-3 (global 3-pool order), CF-4 (mora_since on activation), CF-5 (idempotency). '
    'All payment writes execute in a single PostgreSQL transaction. '
    'Human must apply manually — see runbook in backend/tests/sql/test_process_payment_atomic.sql.';
