from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from enum import Enum


class SavingsStatus(str, Enum):
    ACTIVE = "ACTIVE"
    LIQUIDATED = "LIQUIDATED"


class SavingsContributionCreate(BaseModel):
    client_id: UUID
    contribution_amount: float = Field(..., gt=0)
    contribution_date: Optional[date] = None


class SavingsContributionResponse(BaseModel):
    id: UUID
    user_id: UUID
    client_id: UUID
    contribution_amount: float
    contribution_date: date
    status: SavingsStatus
    liquidated_at: Optional[date]
    created_at: datetime


class SavingsLiquidationResponse(BaseModel):
    id: UUID
    user_id: UUID
    client_id: UUID
    total_contributions: float
    interest_earned: float
    total_delivered: float
    interest_rate: float
    liquidation_date: date
    created_at: datetime
