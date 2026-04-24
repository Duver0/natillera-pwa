from uuid import UUID
from typing import List, Optional

from app.services.base_service import BaseService


class HistoryService(BaseService):

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
