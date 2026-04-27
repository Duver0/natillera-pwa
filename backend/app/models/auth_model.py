from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]


class AuthResponse(BaseModel):
    access_token: str = ""
    refresh_token: str = ""
    user: "UserProfile"
