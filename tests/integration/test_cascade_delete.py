"""
Cascade delete tests — Case 6.

Deleting a client must cascade to:
  - credits (ON DELETE CASCADE via FK)
  - installments (via credits cascade or direct FK)
  - payments (via credits cascade or direct FK)
  - savings (direct FK ON DELETE CASCADE)
  - savings_liquidations (direct FK ON DELETE CASCADE)
  - financial_history: client_id FK is ON DELETE CASCADE

The financial_history immutability trigger only blocks UPDATE/DELETE DML
from user sessions. Cascade deletes from FK constraints fire at the
PostgreSQL engine level and bypass the trigger, so cascade from
client delete IS expected to remove history rows.
"""

import uuid
import pytest
import asyncpg


pytestmark = pytest.mark.asyncio


async def _full_seed(
    conn: asyncpg.Connection, user_id: uuid.UUID
) -> dict[str, uuid.UUID]:
    """
    Seed one of everything attached to a single client.
    Returns a dict of all created IDs.
    """
    client_id = await conn.fetchval(
        """
        INSERT INTO clients (user_id, first_name, last_name, phone)
        VALUES ($1, 'Cascade', 'Test', $2)
        RETURNING id
        """,
        user_id,
        f"+5733{user_id.hex[:8]}",
    )
    credit_id = await conn.fetchval(
        """
        INSERT INTO credits (
            user_id, client_id, initial_capital, pending_capital,
            periodicity, annual_interest_rate, status, start_date
        )
        VALUES ($1, $2, 2000.00, 2000.00, 'WEEKLY', 10.0, 'ACTIVE', CURRENT_DATE)
        RETURNING id
        """,
        user_id,
        client_id,
    )
    installment_id = await conn.fetchval(
        """
        INSERT INTO installments (
            user_id, credit_id, period_number,
            expected_date, expected_value,
            principal_portion, interest_portion
        )
        VALUES ($1, $2, 1, CURRENT_DATE + 7, 200.00, 180.00, 20.00)
        RETURNING id
        """,
        user_id,
        credit_id,
    )
    payment_id = await conn.fetchval(
        """
        INSERT INTO payments (
            user_id, credit_id, amount, payment_date,
            applied_to, recorded_by
        )
        VALUES ($1, $2, 200.00, CURRENT_DATE, '[]'::jsonb, 'test-op')
        RETURNING id
        """,
        user_id,
        credit_id,
    )
    saving_id = await conn.fetchval(
        """
        INSERT INTO savings (user_id, client_id, contribution_amount, contribution_date)
        VALUES ($1, $2, 50.00, CURRENT_DATE)
        RETURNING id
        """,
        user_id,
        client_id,
    )
    liquidation_id = await conn.fetchval(
        """
        INSERT INTO savings_liquidations (
            user_id, client_id,
            total_contributions, interest_earned, total_delivered,
            interest_rate, liquidation_date
        )
        VALUES ($1, $2, 50.00, 2.00, 52.00, 4.0, CURRENT_DATE)
        RETURNING id
        """,
        user_id,
        client_id,
    )
    history_id = await conn.fetchval(
        """
        INSERT INTO financial_history (
            user_id, event_type, client_id, credit_id,
            amount, description, operator_id
        )
        VALUES ($1, 'CLIENT_CREATED', $2, $3, NULL, 'Cascade test seed', 'test-op')
        RETURNING id
        """,
        user_id,
        client_id,
        credit_id,
    )
    return {
        "client_id": client_id,
        "credit_id": credit_id,
        "installment_id": installment_id,
        "payment_id": payment_id,
        "saving_id": saving_id,
        "liquidation_id": liquidation_id,
        "history_id": history_id,
    }


async def _exists(conn: asyncpg.Connection, table: str, row_id: uuid.UUID) -> bool:
    row = await conn.fetchrow(f"SELECT id FROM {table} WHERE id = $1", row_id)
    return row is not None


class TestCascadeDelete:
    async def test_delete_client_cascades_to_all_children(self, raw_conn, user_a_id):
        ids = await _full_seed(raw_conn, user_a_id)

        # Confirm everything exists before delete
        assert await _exists(raw_conn, "clients", ids["client_id"])
        assert await _exists(raw_conn, "credits", ids["credit_id"])
        assert await _exists(raw_conn, "installments", ids["installment_id"])
        assert await _exists(raw_conn, "payments", ids["payment_id"])
        assert await _exists(raw_conn, "savings", ids["saving_id"])
        assert await _exists(raw_conn, "savings_liquidations", ids["liquidation_id"])
        assert await _exists(raw_conn, "financial_history", ids["history_id"])

        # Delete the client
        result = await raw_conn.execute(
            "DELETE FROM clients WHERE id = $1", ids["client_id"]
        )
        assert result == "DELETE 1"

        # All children must be gone
        assert not await _exists(raw_conn, "clients", ids["client_id"]), "client still exists"
        assert not await _exists(raw_conn, "credits", ids["credit_id"]), "credit still exists"
        assert not await _exists(raw_conn, "installments", ids["installment_id"]), "installment still exists"
        assert not await _exists(raw_conn, "payments", ids["payment_id"]), "payment still exists"
        assert not await _exists(raw_conn, "savings", ids["saving_id"]), "saving still exists"
        assert not await _exists(raw_conn, "savings_liquidations", ids["liquidation_id"]), "liquidation still exists"
        assert not await _exists(raw_conn, "financial_history", ids["history_id"]), "history still exists"

    async def test_delete_credit_cascades_to_installments_and_payments(
        self, raw_conn, user_a_id
    ):
        """Deleting a credit (not the whole client) removes its installments and payments."""
        ids = await _full_seed(raw_conn, user_a_id)

        await raw_conn.execute("DELETE FROM credits WHERE id = $1", ids["credit_id"])

        assert not await _exists(raw_conn, "credits", ids["credit_id"])
        assert not await _exists(raw_conn, "installments", ids["installment_id"])
        assert not await _exists(raw_conn, "payments", ids["payment_id"])

        # Savings are attached to client, not credit — must still exist
        assert await _exists(raw_conn, "savings", ids["saving_id"]), (
            "savings should not be deleted when only the credit is removed"
        )

    async def test_other_client_data_unaffected(self, raw_conn, user_a_id):
        """Deleting one client must not touch another client's data."""
        ids_a = await _full_seed(raw_conn, user_a_id)
        ids_b = await _full_seed(raw_conn, user_a_id)

        await raw_conn.execute("DELETE FROM clients WHERE id = $1", ids_a["client_id"])

        # ids_b data must be intact
        assert await _exists(raw_conn, "clients", ids_b["client_id"])
        assert await _exists(raw_conn, "credits", ids_b["credit_id"])
        assert await _exists(raw_conn, "installments", ids_b["installment_id"])
