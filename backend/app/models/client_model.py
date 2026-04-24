from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class ClientCreate(BaseModel):
    first_name: str = Field(..., min_length=2)
    last_name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=7)
    document_id: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)


class ClientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2)
    last_name: Optional[str] = Field(None, min_length=2)
    phone: Optional[str] = Field(None, min_length=7)
    document_id: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)


class ClientResponse(BaseModel):
    id: UUID
    user_id: UUID
    first_name: str
    last_name: str
    phone: str
    document_id: Optional[str]
    address: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    total_debt: Optional[float] = None
    mora_count: Optional[int] = None
