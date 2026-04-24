"""
RLS isolation tests — Cases 1 and 2.

Case 1: User B cannot see or touch User A's data.
Case 2: Inserting a record whose user_id differs from the JWT claim
        is rejected by the WITH CHECK policy.
"""

import uuid
import pytest
import asyncpg


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _insert_client_as(conn: asyncpg.Connection, user_id: uuid.UUID) -> uuid.UUID:
    client_id = await conn.fetchval(
        """
        INSERT INTO clients (user_id, first_name, last_name, phone)
        VALUES ($1, 'Test', 'Client', $2)
        RETURNING id
        """,
        user_id,
        f"+57300{user_id.hex[:7]}",
    )
    return client_id


# ---------------------------------------------------------------------------
# Case 1 — Cross-user isolation
# ---------------------------------------------------------------------------
class TestRLSIsolation:
    async def test_user_b_cannot_select_user_a_client(
        self, raw_conn, as_user, user_a_id, user_b_id
    ):
        """User B's SELECT on clients must return empty even though the row exists."""
        # Seed: insert a client as user A using the raw (superuser) connection
        # We need to bypass RLS for seeding, so we use raw_conn directly.
        client_id = await raw_conn.fetchval(
            """
            INSERT INTO clients (user_id, first_name, last_name, phone)
            VALUES ($1, 'Alice', 'Smith', '+573001111111')
            RETURNING id
            """,
            user_a_id,
        )
        assert client_id is not None

        # Query as user B — must see nothing
        async with as_user(user_b_id) as conn:
            rows = await conn.fetch("SELECT id FROM clients WHERE id = $1", client_id)
        assert len(rows) == 0, "RLS leak: user B should not see user A's client"

    async def test_user_b_cannot_delete_user_a_client(
        self, raw_conn, as_user, user_a_id, user_b_id
    ):
        """DELETE by user B must silently affect 0 rows (RLS filters it out)."""
        client_id = await raw_conn.fetchval(
            """
            INSERT INTO clients (user_id, first_name, last_name, phone)
            VALUES ($1, 'Bob', 'Jones', '+573002222222')
            RETURNING id
            """,
            user_a_id,
        )

        async with as_user(user_b_id) as conn:
            result = await conn.execute(
                "DELETE FROM clients WHERE id = $1", client_id
            )
        deleted_count = int(result.split()[-1])
        assert deleted_count == 0, "RLS leak: user B must not delete user A's client"

        # Confirm row still exists
        row = await raw_conn.fetchrow("SELECT id FROM clients WHERE id = $1", client_id)
        assert row is not None, "Row was wrongly deleted"

    async def test_user_b_cannot_update_user_a_client(
        self, raw_conn, as_user, user_a_id, user_b_id
    ):
        """UPDATE by user B must affect 0 rows."""
        client_id = await raw_conn.fetchval(
            """
            INSERT INTO clients (user_id, first_name, last_name, phone)
            VALUES ($1, 'Carl', 'Doe', '+573003333333')
            RETURNING id
            """,
            user_a_id,
        )

        async with as_user(user_b_id) as conn:
            result = await conn.execute(
                "UPDATE clients SET first_name = 'Hacked' WHERE id = $1", client_id
            )
        updated_count = int(result.split()[-1])
        assert updated_count == 0, "RLS leak: user B must not update user A's client"


# ---------------------------------------------------------------------------
# Case 2 — INSERT with wrong user_id rejected by WITH CHECK
# ---------------------------------------------------------------------------
class TestRLSInsertWrongUser:
    async def test_insert_client_with_foreign_user_id_is_denied(
        self, raw_conn, as_user, user_a_id, user_b_id
    ):
        """
        Authenticating as user_a but providing user_b as user_id must
        be rejected by the WITH CHECK policy on clients.
        """
        async with as_user(user_a_id) as conn:
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.execute(
                    """
                    INSERT INTO clients (user_id, first_name, last_name, phone)
                    VALUES ($1, 'Fake', 'Record', '+573009999999')
                    """,
                    user_b_id,  # wrong: inserting under user_b's ownership while authed as user_a
                )

    async def test_insert_credits_with_foreign_user_id_is_denied(
        self, raw_conn, as_user, user_a_id, user_b_id
    ):
        """Same check on credits table."""
        # First create a legitimate client for user_a to reference
        client_id = await raw_conn.fetchval(
            """
            INSERT INTO clients (user_id, first_name, last_name, phone)
            VALUES ($1, 'Legit', 'Client', '+573004444444')
            RETURNING id
            """,
            user_a_id,
        )

        async with as_user(user_a_id) as conn:
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.execute(
                    """
                    INSERT INTO credits (
                        user_id, client_id, initial_capital, pending_capital,
                        periodicity, annual_interest_rate, status, start_date
                    )
                    VALUES ($1, $2, 1000.00, 1000.00, 'MONTHLY', 12.0, 'ACTIVE', CURRENT_DATE)
                    """,
                    user_b_id,  # wrong user_id
                    client_id,
                )
