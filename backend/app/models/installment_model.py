from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from enum import Enum


class InstallmentStatus(str, Enum):
    UPCOMING = "UPCOMING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    SUSPENDED = "SUSPENDED"


class InstallmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    credit_id: UUID
    period_number: int
    expected_date: date
    expected_value: float
    principal_portion: float
    interest_portion: float
    paid_value: float
    is_overdue: bool
    status: InstallmentStatus
    created_at: datetime
    paid_at: Optional[datetime]
