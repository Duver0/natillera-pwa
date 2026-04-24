from fastapi import APIRouter, Depends, Query
from uuid import UUID

from app.dependencies import get_user_id, get_db
from app.services.savings_service import SavingsService
from app.models.savings_model import SavingsContributionCreate

router = APIRouter()


def _service(db=Depends(get_db), user_id: str = Depends(get_user_id)) -> SavingsService:
    return SavingsService(db, user_id)


@router.post("/contributions", status_code=201)
async def add_contribution(body: SavingsContributionCreate, service: SavingsService = Depends(_service)):
    return await service.add_contribution(body)


@router.post("/liquidate")
async def liquidate(client_id: UUID = Query(...), service: SavingsService = Depends(_service)):
    return await service.liquidate(client_id)


@router.get("/")
async def list_contributions(client_id: UUID = Query(...), service: SavingsService = Depends(_service)):
    return await service.list_contributions(client_id)
