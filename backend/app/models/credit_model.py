from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from enum import Enum


class Periodicity(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"


class CreditStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    SUSPENDED = "SUSPENDED"


class CreditCreate(BaseModel):
    client_id: UUID
    initial_capital: float = Field(..., gt=0)
    periodicity: Periodicity
    annual_interest_rate: float = Field(..., ge=0)
    start_date: date


class CreditResponse(BaseModel):
    id: UUID
    user_id: UUID
    client_id: UUID
    initial_capital: float
    pending_capital: float
    version: int
    periodicity: Periodicity
    annual_interest_rate: float
    status: CreditStatus
    start_date: date
    closed_date: Optional[date]
    next_period_date: Optional[date]
    mora: bool
    mora_since: Optional[date]
    created_at: datetime
    updated_at: datetime
