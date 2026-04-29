"""
Fake Credit Repository — in-memory implementation for testing.
Matches CreditRepository interface exactly.
"""
from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone


class FakeCreditRepository:
    """Fake implementation of CreditRepository for integration testing."""

    def __init__(self, fake_db):
        self._db = fake_db
        self._cache = {}

    async def insert(self, payload: dict) -> dict:
        """Create new credit."""
        credit_id = payload.get("id", str(uuid4()))
        payload["id"] = credit_id
        payload["created_at"] = datetime.now(timezone.utc).isoformat()
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._cache[credit_id] = payload.copy()
        result = await self._db.table("credits").insert(payload).execute()
        return result.data[0]

    async def find_by_id(
        self, credit_id: str, user_id: str
    ) -> Optional[dict]:
        """Find credit by ID + user_id."""
        result = await (
            self._db.table("credits")
            .select("*")
            .eq("id", credit_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    async def find_all(
        self,
        user_id: str,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict]:
        """Find all credits for user."""
        query = self._db.table("credits").select("*").eq("user_id", user_id)
        if client_id:
            query = query.eq("client_id", client_id)
        if status:
            query = query.eq("status", status)
        result = await query.execute()
        return result.data or []

    async def update_with_version(
        self,
        credit_id: str,
        user_id: str,
        expected_version: int,
        patch: dict,
    ) -> dict:
        """Optimistic locking update."""
        patch["version"] = expected_version + 1
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await (
            self._db.table("credits")
            .update(patch)
            .eq("id", credit_id)
            .eq("user_id", user_id)
            .eq("version", expected_version)
            .execute()
        )
        rows = result.data or []
        if not rows:
            raise ValueError("version_conflict")
        return rows[0]

    async def update(
        self, credit_id: str, user_id: str, patch: dict
    ) -> dict:
        """Blind update."""
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await (
            self._db.table("credits")
            .update(patch)
            .eq("id", credit_id)
            .eq("user_id", user_id)
            .execute()
        )
        return (result.data or [{}])[0]

    async def soft_delete(self, credit_id: str, user_id: str) -> None:
        """Soft delete credit."""
        await (
            self._db.table("credits")
            .update({
                "status": "CLOSED",
                "closed_date": datetime.now(timezone.utc).date().isoformat(),
            })
            .eq("id", credit_id)
            .eq("user_id", user_id)
            .execute()
        )

    async def insert_installments(self, installments: list[dict]) -> list[dict]:
        """Insert installments for credit."""
        if not installments:
            return []
        result = await self._db.table("installments").insert(installments).execute()
        return result.data or []

    async def find_installments(
        self,
        credit_id: str,
        status: Optional[str] = None,
    ) -> list[dict]:
        """Find installments for credit."""
        query = (
            self._db.table("installments")
            .select("*")
            .eq("credit_id", credit_id)
            .order("expected_date")
        )
        if status:
            query = query.eq("status", status)
        result = await query.execute()
        return result.data or []

    async def find_overdue_installments(
        self, credit_id: str, today_iso: str
    ) -> list[dict]:
        """Find overdue installments."""
        result = await (
            self._db.table("installments")
            .select(
                "id,expected_date,interest_portion,principal_portion,paid_value,status,is_overdue"
            )
            .eq("credit_id", credit_id)
            .in_("status", ["UPCOMING", "PARTIALLY_PAID"])
            .lt("expected_date", today_iso)
            .execute()
        )
        return result.data or []

    async def mark_installments_overdue(self, ids: list[str]) -> None:
        """Mark installments as overdue."""
        if not ids:
            return
        await (
            self._db.table("installments")
            .update({"is_overdue": True})
            .in_("id", ids)
            .execute()
        )


def create_fake_credit(
    credit_id: str = None,
    user_id: str = "test-user",
    pending_capital: str = "10000.00",
    status: str = "ACTIVE",
) -> dict:
    """Factory para crear credit dict."""
    return {
        "id": credit_id or str(uuid4()),
        "user_id": user_id,
        "client_id": str(uuid4()),
        "initial_capital": pending_capital,
        "pending_capital": pending_capital,
        "version": 1,
        "status": status,
        "mora": False,
        "mora_since": None,
        "annual_interest_rate": "12.00",
        "periodicity": "MONTHLY",
    }