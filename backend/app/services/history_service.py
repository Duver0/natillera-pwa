from uuid import UUID
from typing import Any, List, Optional

from app.services.base_service import BaseService


class HistoryService(BaseService):

    async def record_event(
        self,
        event_type: str,
        client_id: UUID,
        amount: Optional[float],
        description: str,
        operator_id: str,
        credit_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Append-only: insert an immutable FinancialHistory record.
        No update / delete ever touches this table.
        """
        payload: dict[str, Any] = {
            "user_id": self.user_id,
            "event_type": event_type,
            "client_id": str(client_id),
            "credit_id": str(credit_id) if credit_id else None,
            "amount": amount,
            "description": description,
            "metadata": metadata or {},
            "operator_id": operator_id,
        }
        result = await self.db.table("financial_history").insert(payload).execute()
        return (result.data or [{}])[0]

    async def list_events(
        self,
        client_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        query = (
            self.db.table("financial_history")
            .select("*")
            .eq("user_id", self.user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if client_id:
            query = query.eq("client_id", str(client_id))
        if event_type:
            query = query.eq("event_type", event_type)
        result = await query.execute()
        return result.data
