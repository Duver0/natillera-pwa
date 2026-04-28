"""
Credit repository — CRUD async via DatabaseInterface (Supabase / asyncpg).
Optimistic locking: update_with_version() raises ValueError on version mismatch.
No business logic here. Services own the domain rules.
"""
from datetime import datetime, timezone
from typing import Optional


class CreditRepository:
    """Data-access layer for the credits table."""

    def __init__(self, db) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Credits
    # ------------------------------------------------------------------

    async def insert(self, payload: dict) -> dict:
        result = await self._db.table("credits").insert(payload).execute()
        return result.data[0]

    async def find_by_id(self, credit_id: str, user_id: str) -> Optional[dict]:
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
        query = self._db.table("credits").select("*").eq("user_id", user_id)
        if client_id:
            query = query.eq("client_id", client_id)
        if status:
            query = query.eq("status", status)
        result = await query.execute()
        return result.data or []

    async def update_with_version(self, credit_id: str, user_id: str, expected_version: int, patch: dict) -> dict:
        """
        Optimistic locking update.
        Applies patch only when credits.version == expected_version.
        Raises ValueError("version_conflict") if 0 rows updated.
        """
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

    async def update(self, credit_id: str, user_id: str, patch: dict) -> dict:
        """Blind update — use only when optimistic locking is not required."""
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
        await (
            self._db.table("credits")
            .update({"status": "CLOSED", "closed_date": datetime.now(timezone.utc).date().isoformat()})
            .eq("id", credit_id)
            .eq("user_id", user_id)
            .execute()
        )

    # ------------------------------------------------------------------
    # Installments (co-located: same aggregate)
    # ------------------------------------------------------------------

    async def insert_installments(self, installments: list[dict]) -> list[dict]:
        if not installments:
            return []
        result = await self._db.table("installments").insert(installments).execute()
        return result.data or []

    async def find_installments(
        self,
        credit_id: str,
        status: Optional[str] = None,
    ) -> list[dict]:
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

    async def find_overdue_installments(self, credit_id: str, today_iso: str) -> list[dict]:
        result = await (
            self._db.table("installments")
            .select("id,expected_date,interest_portion,principal_portion,paid_value,status,is_overdue")
            .eq("credit_id", credit_id)
            .in_("status", ["UPCOMING", "PARTIALLY_PAID"])
            .lt("expected_date", today_iso)
            .execute()
        )
        return result.data or []

    async def mark_installments_overdue(self, ids: list[str]) -> None:
        if not ids:
            return
        await (
            self._db.table("installments")
            .update({"is_overdue": True})
            .in_("id", ids)
            .execute()
        )
