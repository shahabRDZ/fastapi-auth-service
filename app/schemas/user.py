"""Pydantic schemas for User-related request and response payloads."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Request schemas ────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=100)
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# ── Response schemas ───────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]


class UserPublic(BaseModel):
    """Minimal public user info (safe to expose to other users)."""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    username: str
    full_name: Optional[str]
    created_at: datetime


# ── Token schemas ──────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str          # user id (UUID as string)
    type: str         # "access" | "refresh"
    exp: Optional[int] = None
    iat: Optional[int] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── Generic responses ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
