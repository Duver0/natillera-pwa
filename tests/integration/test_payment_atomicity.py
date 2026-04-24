"""
Payment atomicity test — Case 5.

Scenario: a multi-step payment "transaction" that inserts a payment row
and updates an installment in the same explicit transaction.
If the second statement fails (e.g. CHECK constraint violation), the
entire transaction must roll back — no payment row must persist.

We deliberately trigger a constraint violation on installments.paid_value
(CHECK paid_value >= 0) by passing a negative value to simulate mid-flight
failure.
"""

import uuid
import pytest
import asyncpg


pytestmark = pytest.mark.asyncio


async def _seed_credit_and_installment(
    conn: asyncpg.Connection, user_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Returns (client_id, credit_id, installment_id)."""
    client_id = await conn.fetchval(
        """
        INSERT INTO clients (user_id, first_name, last_name, phone)
        VALUES ($1, 'Atomic', 'Test', $2)
        RETURNING id
        """,
        user_id,
        f"+5732{user_id.hex[:8]}",
    )
    credit_id = await conn.fetchval(
        """
        INSERT INTO credits (
            user_id, client_id, initial_capital, pending_capital,
            periodicity, annual_interest_rate, status, start_date
        )
        VALUES ($1, $2, 3000.00, 3000.00, 'MONTHLY', 18.0, 'ACTIVE', CURRENT_DATE)
        RETURNING id
        """,
        user_id,
        client_id,
    )
    inst_id = await conn.fetchval(
        """
        INSERT INTO installments (
            user_id, credit_id, period_number,
            expected_date, expected_value,
            principal_portion, interest_portion
        )
        VALUES ($1, $2, 1, CURRENT_DATE + 30, 300.00, 250.00, 50.00)
        RETURNING id
        """,
        user_id,
        credit_id,
    )
    return client_id, credit_id, inst_id


class TestPaymentAtomicity:
    async def test_partial_payment_rolls_back_on_constraint_failure(
        self, raw_conn, user_a_id
    ):
        """
        Step 1 succeeds: INSERT payment row.
        Step 2 fails:    UPDATE installments SET paid_value = -999 (violates CHECK).
        Expected: full rollback — no payment row in DB.
        """
        _, credit_id, inst_id = await _seed_credit_and_installment(raw_conn, user_a_id)

        payment_id = None
        try:
            async with raw_conn.transaction():
                # Step 1 — insert payment (valid)
                payment_id = await raw_conn.fetchval(
                    """
                    INSERT INTO payments (
                        user_id, credit_id, amount, payment_date,
                        applied_to, recorded_by
                    )
                    VALUES ($1, $2, 300.00, CURRENT_DATE, '[]'::jsonb, 'test-operator')
                    RETURNING id
                    """,
                    user_a_id,
                    credit_id,
                )
                assert payment_id is not None  # step 1 succeeded in isolation

                # Step 2 — deliberately invalid: negative paid_value triggers CHECK
                await raw_conn.execute(
                    "UPDATE installments SET paid_value = -999 WHERE id = $1",
                    inst_id,
                )
        except asyncpg.CheckViolationError:
            pass  # expected — transaction rolled back by asyncpg
        except Exception:
            pass  # catch any other DB-level error from the constraint

        # Verify the payment row does NOT exist (rollback succeeded)
        if payment_id is not None:
            row = await raw_conn.fetchrow(
                "SELECT id FROM payments WHERE id = $1", payment_id
            )
            assert row is None, (
                "Atomicity failure: payment row persisted after constraint-triggered rollback"
            )

    async def test_successful_payment_commits_both_steps(
        self, raw_conn, user_a_id
    ):
        """
        Sanity test: when both steps are valid the transaction commits
        and both rows reflect the new state.
        """
        _, credit_id, inst_id = await _seed_credit_and_installment(raw_conn, user_a_id)

        async with raw_conn.transaction():
            payment_id = await raw_conn.fetchval(
                """
                INSERT INTO payments (
                    user_id, credit_id, amount, payment_date,
                    applied_to, recorded_by
                )
                VALUES ($1, $2, 300.00, CURRENT_DATE, '[]'::jsonb, 'test-operator')
                RETURNING id
                """,
                user_a_id,
                credit_id,
            )
            await raw_conn.execute(
                "UPDATE installments SET paid_value = 300.00, status = 'PAID', paid_at = NOW() WHERE id = $1",
                inst_id,
            )

        # Both must be visible
        payment_row = await raw_conn.fetchrow("SELECT id FROM payments WHERE id = $1", payment_id)
        inst_row = await raw_conn.fetchrow("SELECT status FROM installments WHERE id = $1", inst_id)
        assert payment_row is not None
        assert inst_row["status"] == "PAID"
