"""Authentication and user schemas for FinPilot AI."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    business_name: str


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token pair returned after authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User profile response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    email: str
    role: str
    created_at: datetime


class BusinessResponse(BaseModel):
    """Business profile response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    currency: str
    country: str
    created_at: datetime
