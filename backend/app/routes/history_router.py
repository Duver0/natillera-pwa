from fastapi import APIRouter, Depends, Query
from typing import Optional
from uuid import UUID

from app.dependencies import get_user_id, get_db
from app.services.history_service import HistoryService

router = APIRouter()


def _service(db=Depends(get_db), user_id: str = Depends(get_user_id)) -> HistoryService:
    return HistoryService(db, user_id)


@router.get("/")
async def list_history(
    client_id: Optional[UUID] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: HistoryService = Depends(_service),
):
    return await service.list_events(client_id=client_id, event_type=event_type, limit=limit, offset=offset)
