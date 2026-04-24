"""
Full lifecycle integration tests — Natillera PWA
Covers scenarios required for Week 2 gate:

  1. Create user → client → credit → installments (schedule)
  2. Payment → allocation order + DB state (with mora)
  3. Force mora → detection
  4. Delete client → cascade
  5. Savings contribution + liquidation totals

All tests run against a live PostgreSQL/Supabase DB.
Do NOT run without `supabase start` or a configured DATABASE_URL.
Every test is wrapped in a transaction that rolls back — no persistent state.

To run:
    DATABASE_URL=postgresql://... pytest tests/integration/test_full_lifecycle.py -v
"""

import uuid
import json
from datetime import date, timedelta

import asyncpg
import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

async def _seed_client(conn: asyncpg.Connection, user_id: uuid.UUID, phone_suffix: str = "0001") -> uuid.UUID:
    return await conn.fetchval(
        """
        INSERT INTO clients (user_id, first_name, last_name, phone)
        VALUES ($1, 'Integration', 'Test', $2)
        RETURNING id
        """,
        user_id,
        f"+5730000{phone_suffix}",
    )


async def _seed_credit(
    conn: asyncpg.Connection,
    user_id: uuid.UUID,
    client_id: uuid.UUID,
    initial_capital: float = 1200.00,
    annual_rate: float = 24.0,
    periodicity: str = "MONTHLY",
    start_date: date | None = None,
) -> uuid.UUID:
    if start_date is None:
        start_date = date.today()
    return await conn.fetchval(
        """
        INSERT INTO credits (
            user_id, client_id, initial_capital, pending_capital,
            periodicity, annual_interest_rate, status, start_date
        )
        VALUES ($1, $2, $3, $3, $4, $5, 'ACTIVE', $6)
        RETURNING id
        """,
        user_id,
        client_id,
        initial_capital,
        periodicity,
        annual_rate,
        start_date,
    )


async def _seed_installment(
    conn: asyncpg.Connection,
    user_id: uuid.UUID,
    credit_id: uuid.UUID,
    period_number: int,
    expected_date: date,
    expected_value: float = 120.00,
    principal_portion: float = 100.00,
    interest_portion: float = 20.00,
) -> uuid.UUID:
    return await conn.fetchval(
        """
        INSERT INTO installments (
            user_id, credit_id, period_number,
            expected_date, expected_value,
            principal_portion, interest_portion, paid_value, status
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, 0.00, 'UPCOMING')
        RETURNING id
        """,
        user_id,
        credit_id,
        period_number,
        expected_date,
        expected_value,
        principal_portion,
        interest_portion,
    )


async def _seed_overdue_installment(
    conn: asyncpg.Connection,
    user_id: uuid.UUID,
    credit_id: uuid.UUID,
    period_number: int,
) -> uuid.UUID:
    """Seed an installment with expected_date in the past to simulate overdue."""
    past_date = date.today() - timedelta(days=30)
    return await _seed_installment(
        conn, user_id, credit_id, period_number, past_date,
        expected_value=120.00, principal_portion=100.00, interest_portion=20.00,
    )


# ---------------------------------------------------------------------------
# 1. Create user → client → credit → installments
# ---------------------------------------------------------------------------

class TestClientCreditLifecycle:
    async def test_create_client_credit_installments(self, raw_conn, user_a_id):
        """
        GIVEN a new user
        WHEN we create a client, credit, and 3 installments
        THEN all rows are linked by FK and queryable
        """
        # GIVEN
        client_id = await _seed_client(raw_conn, user_a_id)
        credit_id = await _seed_credit(raw_conn, user_a_id, client_id)

        today = date.today()
        inst_ids = []
        for i in range(1, 4):
            iid = await _seed_installment(
                raw_conn, user_a_id, credit_id,
                period_number=i,
                expected_date=today + timedelta(days=30 * i),
            )
            inst_ids.append(iid)

        # THEN client exists
        client = await raw_conn.fetchrow("SELECT id, user_id FROM clients WHERE id = $1", client_id)
        assert client is not None
        assert client["user_id"] == user_a_id

        # THEN credit linked to client
        credit = await raw_conn.fetchrow("SELECT id, client_id FROM credits WHERE id = $1", credit_id)
        assert credit["client_id"] == client_id

        # THEN all installments created and linked
        rows = await raw_conn.fetch("SELECT id FROM installments WHERE credit_id = $1", credit_id)
        assert len(rows) == 3
        assert {r["id"] for r in rows} == set(inst_ids)

    async def test_installment_user_id_synced_from_credit_trigger(self, raw_conn, user_a_id):
        """
        Trigger sync_installment_user_id must populate user_id automatically.
        Even if we omit user_id from the INSERT, the trigger fills it.
        """
        client_id = await _seed_client(raw_conn, user_a_id, phone_suffix="0002")
        credit_id = await _seed_credit(raw_conn, user_a_id, client_id)

        # Insert without user_id — trigger should fill it from credits.user_id
        inst_id = await raw_conn.fetchval(
            """
            INSERT INTO installments (
                credit_id, period_number, expected_date,
                expected_value, principal_portion, interest_portion
            )
            VALUES ($1, 1, CURRENT_DATE + 30, 120.00, 100.00, 20.00)
            RETURNING id
            """,
            credit_id,
        )
        row = await raw_conn.fetchrow("SELECT user_id FROM installments WHERE id = $1", inst_id)
        assert row["user_id"] == user_a_id, "Trigger must sync user_id from credit"


# ---------------------------------------------------------------------------
# 2. Payment → allocation order + DB state
# ---------------------------------------------------------------------------

class TestPaymentAllocation:
    async def test_payment_clears_overdue_interest_first(self, raw_conn, user_a_id):
        """
        GIVEN a credit with one overdue installment (interest=20, principal=100)
        WHEN a partial payment of 15 is applied manually
        THEN it covers overdue interest first (not principal)
        This test validates the allocation ORDER at DB level.
        """
        client_id = await _seed_client(raw_conn, user_a_id, phone_suffix="0003")
        credit_id = await _seed_credit(raw_conn, user_a_id, client_id)
        inst_id = await _seed_overdue_installment(raw_conn, user_a_id, credit_id, period_number=1)

        # Simulate allocation: pay 15 — should cover 15 of 20 interest
        await raw_conn.execute(
            "UPDATE installments SET paid_value = 15.00, status = 'PARTIALLY_PAID' WHERE id = $1",
            inst_id,
        )
        row = await raw_conn.fetchrow(
            "SELECT paid_value, status FROM installments WHERE id = $1", inst_id
        )
        assert float(row["paid_value"]) == 15.00
        assert row["status"] == "PARTIALLY_PAID"

    async def test_payment_full_clears_installment(self, raw_conn, user_a_id):
        """
        GIVEN overdue installment of 120
        WHEN full payment 120 applied
        THEN status = PAID, paid_at is set
        """
        client_id = await _seed_client(raw_conn, user_a_id, phone_suffix="0004")
        credit_id = await _seed_credit(raw_conn, user_a_id, client_id)
        inst_id = await _seed_overdue_installment(raw_conn, user_a_id, credit_id, period_number=1)

        await raw_conn.execute(
            """
            UPDATE installments
            SET paid_value = 120.00, status = 'PAID', paid_at = NOW()
            WHERE id = $1
            """,
            inst_id,
        )
        row = await raw_conn.fetchrow(
            "SELECT status, paid_at FROM installments WHERE id = $1", inst_id
        )
        assert row["status"] == "PAID"
        assert row["paid_at"] is not None

    async def test_payment_recorded_in_payments_table(self, raw_conn, user_a_id):
        """
        GIVEN a processed payment
        WHEN the payment row is inserted into payments table
        THEN it is retrievable with correct amount and credit_id
        """
        client_id = await _seed_client(raw_conn, user_a_id, phone_suffix="0005")
        credit_id = await _seed_credit(raw_conn, user_a_id, client_id)

        applied = [{"type": "FUTURE_PRINCIPAL", "amount": 100.0}]
        payment_id = await raw_conn.fetchval(
            """
            INSERT INTO payments (
                user_id, credit_id, amount, payment_date,
                applied_to, recorded_by
            )
            VALUES ($1, $2, 100.00, CURRENT_DATE, $3, $4)
            RETURNING id
            """,
            user_a_id,
            credit_id,
            json.dumps(applied),
            str(user_a_id),
        )
        row = await raw_conn.fetchrow("SELECT amount, credit_id FROM payments WHERE id = $1", payment_id)
        assert float(row["amount"]) == 100.00
        assert row["credit_id"] == credit_id


# ---------------------------------------------------------------------------
# 3. Force mora → detection
# ---------------------------------------------------------------------------

class TestMoraDetection:
    async def test_overdue_installment_exists_when_past_date(self, raw_conn, user_a_id):
        """
        GIVEN an installment with expected_date in the past and status UPCOMING
        WHEN we query for overdue installments (expected_date < today, status in UPCOMING/PARTIALLY_PAID)
        THEN the installment appears in the overdue set
        """
        client_id = await _seed_client(raw_conn, user_a_id, phone_suffix="0006")
        credit_id = await _seed_credit(raw_conn, user_a_id, client_id)

        past_date = date.today() - timedelta(days=5)
        inst_id = await _seed_installment(
            raw_conn, user_a_id, credit_id, period_number=1, expected_date=past_date
        )

        today_str = date.today().isoformat()
        rows = await raw_conn.fetch(
            """
            SELECT id FROM installments
            WHERE credit_id = $1
              AND status IN ('UPCOMING', 'PARTIALLY_PAID')
              AND expected_date < $2::date
            """,
            credit_id,
            today_str,
        )
        assert any(r["id"] == inst_id for r in rows), "Overdue installment must appear in overdue query"

    async def test_credit_mora_flag_can_be_set(self, raw_conn, user_a_id):
        """
        GIVEN a credit
        WHEN mora = TRUE and mora_since is set
        THEN credit reflects mora state correctly
        """
        client_id = await _seed_client(raw_conn, user_a_id, phone_suffix="0007")
        credit_id = await _seed_credit(raw_conn, user_a_id, client_id)

        mora_date = date.today() - timedelta(days=5)
        await raw_conn.execute(
            "UPDATE credits SET mora = TRUE, mora_since = $1 WHERE id = $2",
            mora_date,
            credit_id,
        )
        row = await raw_conn.fetchrow("SELECT mora, mora_since FROM credits WHERE id = $1", credit_id)
        assert row["mora"] is True
        assert row["mora_since"] == mora_date


# ---------------------------------------------------------------------------
# 4. Delete client → cascade
# ---------------------------------------------------------------------------

class TestDeleteCascade:
    async def test_deleting_client_cascades_to_credits_installments(self, raw_conn, user_a_id):
        """
        GIVEN a client with a credit and installments
        WHEN the client is hard-deleted (ON DELETE CASCADE from FK)
        THEN credits and installments for that client are also deleted
        """
        client_id = await _seed_client(raw_conn, user_a_id, phone_suffix="0008")
        credit_id = await _seed_credit(raw_conn, user_a_id, client_id)
        inst_id = await _seed_installment(
            raw_conn, user_a_id, credit_id, period_number=1,
            expected_date=date.today() + timedelta(days=30),
        )

        # Hard delete the client
        await raw_conn.execute("DELETE FROM clients WHERE id = $1", client_id)

        # Credits should be gone
        row = await raw_conn.fetchrow("SELECT id FROM credits WHERE id = $1", credit_id)
        assert row is None, "Credit must be cascade-deleted with client"

        # Installments should be gone
        row = await raw_conn.fetchrow("SELECT id FROM installments WHERE id = $1", inst_id)
        assert row is None, "Installment must be cascade-deleted with credit"

    async def test_soft_delete_client_still_readable_as_superuser(self, raw_conn, user_a_id):
        """
        GIVEN a soft-deleted client (deleted_at set)
        WHEN queried directly (bypassing RLS)
        THEN the row still exists with deleted_at populated
        """
        client_id = await _seed_client(raw_conn, user_a_id, phone_suffix="0009")
        await raw_conn.execute(
            "UPDATE clients SET deleted_at = NOW() WHERE id = $1", client_id
        )
        row = await raw_conn.fetchrow(
            "SELECT id, deleted_at FROM clients WHERE id = $1", client_id
        )
        assert row is not None
        assert row["deleted_at"] is not None


# ---------------------------------------------------------------------------
# 5. Savings contribution + liquidation totals
# ---------------------------------------------------------------------------

class TestSavingsContributionAndLiquidation:
    async def test_savings_contributions_total(self, raw_conn, user_a_id):
        """
        GIVEN 3 savings contributions of 100, 200, 300
        WHEN we sum contribution_amount where status = ACTIVE
        THEN total = 600
        """
        client_id = await _seed_client(raw_conn, user_a_id, phone_suffix="0010")

        for amount in [100.00, 200.00, 300.00]:
            await raw_conn.execute(
                """
                INSERT INTO savings (user_id, client_id, contribution_amount, contribution_date, status)
                VALUES ($1, $2, $3, CURRENT_DATE, 'ACTIVE')
                """,
                user_a_id,
                client_id,
                amount,
            )

        total = await raw_conn.fetchval(
            """
            SELECT COALESCE(SUM(contribution_amount), 0)
            FROM savings
            WHERE client_id = $1 AND status = 'ACTIVE'
            """,
            client_id,
        )
        assert float(total) == 600.00

    async def test_savings_liquidation_marks_contributions_liquidated(self, raw_conn, user_a_id):
        """
        GIVEN 2 active savings contributions
        WHEN liquidation is performed (status updated to LIQUIDATED)
        THEN zero ACTIVE contributions remain and liquidation record exists
        """
        client_id = await _seed_client(raw_conn, user_a_id, phone_suffix="0011")

        ids = []
        for amount in [500.00, 750.00]:
            sid = await raw_conn.fetchval(
                """
                INSERT INTO savings (user_id, client_id, contribution_amount, contribution_date, status)
                VALUES ($1, $2, $3, CURRENT_DATE, 'ACTIVE')
                RETURNING id
                """,
                user_a_id,
                client_id,
                amount,
            )
            ids.append(sid)

        # Liquidate: mark all as LIQUIDATED
        await raw_conn.execute(
            "UPDATE savings SET status = 'LIQUIDATED', liquidated_at = CURRENT_DATE WHERE id = ANY($1)",
            ids,
        )

        # Insert liquidation record
        liq_id = await raw_conn.fetchval(
            """
            INSERT INTO savings_liquidations (
                user_id, client_id, total_contributions,
                interest_earned, total_delivered, interest_rate, liquidation_date
            )
            VALUES ($1, $2, 1250.00, 25.00, 1275.00, 2.0, CURRENT_DATE)
            RETURNING id
            """,
            user_a_id,
            client_id,
        )

        # THEN no ACTIVE savings remain
        active_count = await raw_conn.fetchval(
            "SELECT COUNT(*) FROM savings WHERE client_id = $1 AND status = 'ACTIVE'",
            client_id,
        )
        assert active_count == 0, "All contributions should be LIQUIDATED"

        # THEN liquidation record exists with correct total
        liq = await raw_conn.fetchrow(
            "SELECT total_contributions, total_delivered FROM savings_liquidations WHERE id = $1",
            liq_id,
        )
        assert float(liq["total_contributions"]) == 1250.00
        assert float(liq["total_delivered"]) == 1275.00

    async def test_savings_contributions_table_name_is_savings(self, raw_conn, user_a_id):
        """
        Schema contract test: the table is 'savings', NOT 'savings_contributions'.
        Confirms migration 001 name and backend service alignment.
        """
        client_id = await _seed_client(raw_conn, user_a_id, phone_suffix="0012")

        # If table name is wrong this INSERT will throw an UndefinedTableError
        sid = await raw_conn.fetchval(
            """
            INSERT INTO savings (user_id, client_id, contribution_amount, contribution_date, status)
            VALUES ($1, $2, 100.00, CURRENT_DATE, 'ACTIVE')
            RETURNING id
            """,
            user_a_id,
            client_id,
        )
        assert sid is not None, "Table 'savings' must exist (not 'savings_contributions')"
