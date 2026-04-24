from uuid import UUID
from datetime import datetime, timezone
from typing import List, Optional

from app.services.base_service import BaseService
from app.models.client_model import ClientCreate, ClientUpdate


class ClientService(BaseService):

    async def create(self, body: ClientCreate) -> dict:
        payload = {
            "user_id": self.user_id,
            "first_name": body.first_name,
            "last_name": body.last_name,
            "phone": body.phone,
            "document_id": body.document_id,
            "address": body.address,
            "notes": body.notes,
        }
        result = await self.db.table("clients").insert(payload).execute()
        return result.data[0]

    async def list_all(
        self,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Return paginated clients: {items, total, limit, offset}."""
        base_query = (
            self.db.table("clients")
            .select("*", count="exact")
            .eq("user_id", self.user_id)
            .is_("deleted_at", "null")
        )
        if search:
            base_query = base_query.or_(
                f"first_name.ilike.%{search}%,last_name.ilike.%{search}%,phone.ilike.%{search}%"
            )
        result = await base_query.range(offset, offset + limit - 1).execute()
        total = result.count if result.count is not None else len(result.data)
        return {
            "items": result.data,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_by_id(self, client_id: UUID) -> dict:
        result = await (
            self.db.table("clients")
            .select("*")
            .eq("id", str(client_id))
            .eq("user_id", self.user_id)
            .is_("deleted_at", "null")
            .single()
            .execute()
        )
        if not result.data:
            self._raise_forbidden("client")
        return result.data

    async def update(self, client_id: UUID, body: ClientUpdate) -> dict:
        await self.get_by_id(client_id)  # Ownership check
        patch = {k: v for k, v in body.model_dump().items() if v is not None}
        result = await (
            self.db.table("clients")
            .update(patch)
            .eq("id", str(client_id))
            .eq("user_id", self.user_id)
            .execute()
        )
        return result.data[0]

    async def get_summary(self, client_id: UUID) -> dict:
        """Aggregate: active credits, total pending capital, total overdue, mora count, savings total."""
        await self.get_by_id(client_id)  # Ownership check + 403 if not found

        credits_result = await (
            self.db.table("credits")
            .select("id,status,pending_capital,mora")
            .eq("client_id", str(client_id))
            .eq("user_id", self.user_id)
            .execute()
        )
        credits = credits_result.data or []
        active_credits = [c for c in credits if c["status"] == "ACTIVE"]

        total_pending_capital = sum(float(c["pending_capital"]) for c in active_credits)
        mora_count = sum(1 for c in active_credits if c["mora"])

        # Overdue total: sum of expected_value - paid_value for overdue installments
        active_ids = [c["id"] for c in active_credits]
        total_overdue = 0.0
        if active_ids:
            from datetime import date
            today = date.today().isoformat()
            overdue_result = await (
                self.db.table("installments")
                .select("expected_value,paid_value")
                .in_("credit_id", active_ids)
                .in_("status", ["UPCOMING", "PARTIALLY_PAID"])
                .lt("expected_date", today)
                .execute()
            )
            for inst in (overdue_result.data or []):
                total_overdue += float(inst["expected_value"]) - float(inst["paid_value"])

        # Savings total — table name from migration 001_initial_schema.sql is "savings"
        savings_result = await (
            self.db.table("savings")
            .select("contribution_amount")
            .eq("client_id", str(client_id))
            .eq("user_id", self.user_id)
            .eq("status", "ACTIVE")
            .execute()
        )
        savings_total = sum(float(s["contribution_amount"]) for s in (savings_result.data or []))

        return {
            "client_id": str(client_id),
            "active_credits_count": len(active_credits),
            "total_pending_capital": total_pending_capital,
            "total_overdue": round(total_overdue, 2),
            "mora_count": mora_count,
            "savings_total": savings_total,
        }

    async def delete(self, client_id: UUID) -> None:
        await self.get_by_id(client_id)  # Ownership check
        now = datetime.now(timezone.utc).isoformat()
        await (
            self.db.table("clients")
            .update({"deleted_at": now})
            .eq("id", str(client_id))
            .eq("user_id", self.user_id)
            .execute()
        )
