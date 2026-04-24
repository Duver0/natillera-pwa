from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime
from uuid import UUID
from enum import Enum


class EventType(str, Enum):
    CREDIT_CREATED = "CREDIT_CREATED"
    CREDIT_CLOSED = "CREDIT_CLOSED"
    CREDIT_SUSPENDED = "CREDIT_SUSPENDED"
    INSTALLMENT_GENERATED = "INSTALLMENT_GENERATED"
    PAYMENT_RECORDED = "PAYMENT_RECORDED"
    SAVINGS_CONTRIBUTION = "SAVINGS_CONTRIBUTION"
    SAVINGS_LIQUIDATION = "SAVINGS_LIQUIDATION"
    CLIENT_CREATED = "CLIENT_CREATED"
    CLIENT_DELETED = "CLIENT_DELETED"


class HistoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    event_type: EventType
    client_id: UUID
    credit_id: Optional[UUID]
    amount: Optional[float]
    description: str
    metadata: Optional[Dict[str, Any]]
    operator_id: str
    created_at: datetime
