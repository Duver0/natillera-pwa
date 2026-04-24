"""
Trigger tests — Cases 3 and 4.

Case 3: Locked installment fields (expected_value, principal_portion,
        interest_portion, period_number, expected_date) must be immutable
        after INSERT.

Case 4: financial_history is append-only — UPDATE and DELETE must raise.
"""

import uuid
import pytest
import asyncpg


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Seed helpers (all run through raw_conn / superuser to bypass RLS)
# ---------------------------------------------------------------------------
async def _seed_credit(conn: asyncpg.Connection, user_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """Returns (client_id, credit_id)."""
    client_id = await conn.fetchval(
        """
        INSERT INTO clients (user_id, first_name, last_name, phone)
        VALUES ($1, 'Trigger', 'User', $2)
        RETURNING id
        """,
        user_id,
        f"+5731{user_id.hex[:8]}",
    )
    credit_id = await conn.fetchval(
        """
        INSERT INTO credits (
            user_id, client_id, initial_capital, pending_capital,
            periodicity, annual_interest_rate, status, start_date
        )
        VALUES ($1, $2, 5000.00, 5000.00, 'MONTHLY', 24.0, 'ACTIVE', CURRENT_DATE)
        RETURNING id
        """,
        user_id,
        client_id,
    )
    return client_id, credit_id


async def _seed_installment(
    conn: asyncpg.Connection, user_id: uuid.UUID, credit_id: uuid.UUID
) -> uuid.UUID:
    inst_id = await conn.fetchval(
        """
        INSERT INTO installments (
            user_id, credit_id, period_number,
            expected_date, expected_value,
            principal_portion, interest_portion
        )
        VALUES ($1, $2, 1, CURRENT_DATE + 30, 600.00, 500.00, 100.00)
        RETURNING id
        """,
        user_id,
        credit_id,
    )
    return inst_id


async def _seed_history_event(
    conn: asyncpg.Connection,
    user_id: uuid.UUID,
    client_id: uuid.UUID,
    credit_id: uuid.UUID,
) -> uuid.UUID:
    event_id = await conn.fetchval(
        """
        INSERT INTO financial_history (
            user_id, event_type, client_id, credit_id,
            amount, description, operator_id
        )
        VALUES ($1, 'CREDIT_CREATED', $2, $3, 5000.00, 'Test event', 'test-operator')
        RETURNING id
        """,
        user_id,
        client_id,
        credit_id,
    )
    return event_id


# ---------------------------------------------------------------------------
# Case 3 — Installment locked fields
# ---------------------------------------------------------------------------
class TestInstallmentImmutability:
    @pytest.mark.parametrize(
        "field,new_value",
        [
            ("expected_value", "999.00"),
            ("principal_portion", "1.00"),
            ("interest_portion", "1.00"),
            ("period_number", "99"),
            ("expected_date", "CURRENT_DATE + 999"),
        ],
    )
    async def test_locked_field_update_is_blocked(
        self, raw_conn, user_a_id, field, new_value
    ):
        _, credit_id = await _seed_credit(raw_conn, user_a_id)
        inst_id = await _seed_installment(raw_conn, user_a_id, credit_id)

        with pytest.raises(asyncpg.exceptions.RaiseError) as exc_info:
            await raw_conn.execute(
                f"UPDATE installments SET {field} = {new_value} WHERE id = $1",
                inst_id,
            )
        assert "immutable" in str(exc_info.value).lower(), (
            f"Expected immutability error for {field}, got: {exc_info.value}"
        )

    async def test_mutable_field_update_succeeds(self, raw_conn, user_a_id):
        """Sanity: updating status (a mutable field) must not raise."""
        _, credit_id = await _seed_credit(raw_conn, user_a_id)
        inst_id = await _seed_installment(raw_conn, user_a_id, credit_id)

        await raw_conn.execute(
            "UPDATE installments SET status = 'PAID', paid_value = 600.00, paid_at = NOW() WHERE id = $1",
            inst_id,
        )
        row = await raw_conn.fetchrow("SELECT status FROM installments WHERE id = $1", inst_id)
        assert row["status"] == "PAID"


# ---------------------------------------------------------------------------
# Case 4 — financial_history append-only
# ---------------------------------------------------------------------------
class TestHistoryAppendOnly:
    async def test_update_history_is_blocked(self, raw_conn, user_a_id):
        client_id, credit_id = await _seed_credit(raw_conn, user_a_id)
        event_id = await _seed_history_event(raw_conn, user_a_id, client_id, credit_id)

        with pytest.raises(asyncpg.exceptions.RaiseError) as exc_info:
            await raw_conn.execute(
                "UPDATE financial_history SET description = 'tampered' WHERE id = $1",
                event_id,
            )
        assert "immutable" in str(exc_info.value).lower()

    async def test_delete_history_is_blocked(self, raw_conn, user_a_id):
        client_id, credit_id = await _seed_credit(raw_conn, user_a_id)
        event_id = await _seed_history_event(raw_conn, user_a_id, client_id, credit_id)

        with pytest.raises(asyncpg.exceptions.RaiseError) as exc_info:
            await raw_conn.execute(
                "DELETE FROM financial_history WHERE id = $1", event_id
            )
        assert "immutable" in str(exc_info.value).lower()

    async def test_history_insert_succeeds(self, raw_conn, user_a_id):
        """Inserts into financial_history must work (append is allowed)."""
        client_id, credit_id = await _seed_credit(raw_conn, user_a_id)
        event_id = await _seed_history_event(raw_conn, user_a_id, client_id, credit_id)
        assert event_id is not None

    async def test_history_delete_via_rls_also_blocked(
        self, as_user, raw_conn, user_a_id
    ):
        """
        Even as the owning user, the trigger must block DELETE on history.
        (RLS has no DELETE policy, but the trigger fires before RLS can
        silently swallow the row — confirm trigger wins.)
        """
        client_id, credit_id = await _seed_credit(raw_conn, user_a_id)
        event_id = await _seed_history_event(raw_conn, user_a_id, client_id, credit_id)

        async with as_user(user_a_id) as conn:
            with pytest.raises(asyncpg.exceptions.RaiseError):
                await conn.execute(
                    "DELETE FROM financial_history WHERE id = $1", event_id
                )
