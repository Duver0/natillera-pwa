from fastapi import APIRouter, Depends, Query
from uuid import UUID
from pydantic import BaseModel, Field

from app.dependencies import get_user_id, get_db
from app.services.payment_service import PaymentService
from app.models.payment_model import PaymentRequest

router = APIRouter()


class PaymentPreviewRequest(BaseModel):
    credit_id: UUID
    amount: float = Field(..., gt=0)


def _service(db=Depends(get_db), user_id: str = Depends(get_user_id)) -> PaymentService:
    return PaymentService(db, user_id)


@router.post("/preview")
async def preview_payment(body: PaymentPreviewRequest, service: PaymentService = Depends(_service)):
    """Dry-run allocation — no DB writes."""
    return await service.preview_payment(body.credit_id, body.amount)


@router.post("/", status_code=201)
async def process_payment(body: PaymentRequest, service: PaymentService = Depends(_service)):
    return await service.process_payment(body)


@router.get("/")
async def list_payments(credit_id: UUID = Query(...), service: PaymentService = Depends(_service)):
    return await service.list_payments(credit_id)
