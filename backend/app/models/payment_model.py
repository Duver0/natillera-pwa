from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID


class PaymentAppliedTo(BaseModel):
    type: str  # OVERDUE_INTEREST | OVERDUE_PRINCIPAL | FUTURE_PRINCIPAL
    amount: float
    installment_id: Optional[str] = None


class PaymentRequest(BaseModel):
    credit_id: UUID
    amount: float = Field(..., gt=0)
    payment_date: Optional[date] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: UUID
    user_id: UUID
    credit_id: UUID
    amount: float
    payment_date: date
    applied_to: List[PaymentAppliedTo]
    notes: Optional[str]
    recorded_by: str
    created_at: datetime
