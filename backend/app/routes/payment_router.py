"""
Payment router — Phase 4.
Contract: .github/specs/payment-contract.md

POST /payments        → 201 PaymentResponse | 400 | 409 | 422 | 403
POST /payments/preview → 200 PaymentPreviewResponse | 400 | 422 | 403
GET  /payments        → list (legacy)
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from uuid import UUID

from app.dependencies import get_user_id, get_db
from app.services.payment_service import PaymentService, VersionConflict
from app.models.payment_model import (
    PaymentRequest,
    PaymentPreviewRequest,
    PaymentResponse,
    PaymentPreviewResponse,
)

router = APIRouter()


def _service(db=Depends(get_db), user_id: str = Depends(get_user_id)) -> PaymentService:
    return PaymentService(db, user_id)


@router.post("/preview", response_model=PaymentPreviewResponse, status_code=200)
async def preview_payment(
    body: PaymentPreviewRequest,
    service: PaymentService = Depends(_service),
):
    """Dry-run allocation — no DB writes. Returns breakdown + projected credit snapshot."""
    return await service.preview_payment_breakdown(body.credit_id, body.amount)


@router.post("/", response_model=PaymentResponse, status_code=201)
async def process_payment(
    body: PaymentRequest,
    service: PaymentService = Depends(_service),
):
    """
    Process payment in mandatory order.
    409 on optimistic lock conflict — client must retry.
    """
    try:
        return await service.process_payment(body)
    except VersionConflict:
        raise HTTPException(status_code=409, detail="credit_version_conflict_retry")


@router.get("/")
async def list_payments(
    credit_id: UUID = Query(...),
    service: PaymentService = Depends(_service),
):
    return await service.list_payments(credit_id)
