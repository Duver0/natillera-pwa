"""
Payment Pydantic schemas — Phase 4 refactor.
Contract: .github/specs/payment-contract.md

All monetary fields use Decimal. No float.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import date
from decimal import Decimal
from uuid import UUID


class PaymentRequest(BaseModel):
    credit_id: UUID
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    operator_id: str = Field(..., min_length=1)
    idempotency_key: Optional[UUID] = None
    # Legacy optional fields kept for backwards compat
    payment_date: Optional[date] = None
    notes: Optional[str] = None


class PaymentPreviewRequest(BaseModel):
    credit_id: UUID
    amount: Decimal = Field(..., gt=0, decimal_places=2)


class AppliedToEntry(BaseModel):
    installment_id: UUID
    type: Literal["OVERDUE_INTEREST", "OVERDUE_PRINCIPAL", "FUTURE_PRINCIPAL"]
    amount: Decimal


class UpdatedCreditSnapshot(BaseModel):
    pending_capital: Decimal
    mora: bool
    version: int


class PaymentResponse(BaseModel):
    payment_id: UUID
    credit_id: UUID
    total_amount: Decimal
    applied_to: List[AppliedToEntry]
    updated_credit_snapshot: UpdatedCreditSnapshot


class PaymentPreviewResponse(BaseModel):
    credit_id: UUID
    total_amount: Decimal
    applied_to: List[AppliedToEntry]
    unallocated: Decimal
    updated_credit_snapshot: UpdatedCreditSnapshot
