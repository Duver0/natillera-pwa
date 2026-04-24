from fastapi import APIRouter, Depends, Query
from typing import Optional
from uuid import UUID

from app.dependencies import get_user_id, get_db
from app.services.installment_service import InstallmentService

router = APIRouter()


def _service(db=Depends(get_db), user_id: str = Depends(get_user_id)) -> InstallmentService:
    return InstallmentService(db, user_id)


@router.get("/")
async def list_installments(
    credit_id: UUID = Query(...),
    status: Optional[str] = Query(None),
    service: InstallmentService = Depends(_service),
):
    return await service.list_for_credit(credit_id, status=status)


@router.post("/generate")
async def generate_installment(credit_id: UUID = Query(...), service: InstallmentService = Depends(_service)):
    return await service.generate_next(credit_id)
