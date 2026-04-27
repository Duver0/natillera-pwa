from fastapi import APIRouter, Depends, Query
from typing import Optional
from uuid import UUID

from app.dependencies import get_user_id, get_db
from app.services.credit_service import CreditService
from app.services.installment_service import InstallmentService
from app.models.credit_model import CreditCreate

router = APIRouter()


def _service(db=Depends(get_db), user_id: str = Depends(get_user_id)) -> CreditService:
    return CreditService(db, user_id)


def _inst_service(db=Depends(get_db), user_id: str = Depends(get_user_id)) -> InstallmentService:
    return InstallmentService(db, user_id)


@router.get("/")
async def list_credits(
    client_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    service: CreditService = Depends(_service),
):
    return await service.list_all(client_id=client_id, status=status)


@router.post("/", status_code=201)
async def create_credit(body: CreditCreate, service: CreditService = Depends(_service)):
    return await service.create(body)


@router.get("/{credit_id}")
async def get_credit(credit_id: UUID, service: CreditService = Depends(_service)):
    return await service.get_by_id(credit_id)


@router.get("/{credit_id}/installments")
async def list_credit_installments(
    credit_id: UUID,
    status: Optional[str] = Query(None, description="Filter by installment status: UPCOMING, PARTIALLY_PAID, PAID, SUSPENDED"),
    service: InstallmentService = Depends(_inst_service),
):
    """List all installments for a credit, optionally filtered by status."""
    return await service.list_for_credit(credit_id, status=status)
