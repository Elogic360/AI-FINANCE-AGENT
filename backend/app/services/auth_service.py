"""Authentication & registration business logic.

Uses bcrypt DIRECTLY (not passlib) for password hashing and
python-jose for JWT creation/verification.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.business import Business, User

settings = get_settings()


# ── Password helpers ─────────────────────────────────────────────


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plaintext password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify *plain* against the bcrypt *hashed* value."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT helpers ──────────────────────────────────────────────────


def create_token(user_id: uuid.UUID, token_type: str = "access") -> str:
    now = datetime.now(timezone.utc)
    if token_type == "access":
        expires = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        expires = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "type": token_type,
        "exp": expires,
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT. Returns the payload or None on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


# ── Service functions ────────────────────────────────────────────


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    business_name: str,
) -> dict:
    """Create a new Business + User and return tokens."""
    # Check for existing email
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create business
    business = Business(
        name=business_name,
        currency=settings.DEFAULT_CURRENCY,
        country=settings.DEFAULT_COUNTRY,
    )
    db.add(business)
    await db.flush()  # get business.id without committing yet

    # Create user
    user = User(
        business_id=business.id,
        email=email,
        hashed_password=hash_password(password),
        role="owner",
    )
    db.add(user)
    await db.flush()

    # Generate tokens
    access_token = create_token(user.id, "access")
    refresh_token = create_token(user.id, "refresh")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
        "business": business,
    }


async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> dict:
    """Authenticate credentials and return tokens."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_token(user.id, "access")
    refresh_token = create_token(user.id, "refresh")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def get_user_by_id(db: AsyncSession, user_id: str | uuid.UUID) -> Optional[User]:
    """Return the user record or None.

    *user_id* may be a ``str`` (from a JWT ``sub`` claim) or a ``uuid.UUID``.
    SQLAlchemy auto-coerces the string to UUID for the WHERE clause.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
