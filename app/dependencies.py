"""FastAPI dependency injection helpers."""

import uuid
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth import decode_token

security = HTTPBearer()

# ── Redis client (module-level singleton, initialised in lifespan) ─────────────
_redis_client: aioredis.Redis | None = None


def set_redis_client(client: aioredis.Redis) -> None:
    global _redis_client
    _redis_client = client


def get_redis() -> aioredis.Redis:
    if _redis_client is None:
        raise RuntimeError("Redis client not initialised")
    return _redis_client


# ── Token blocklist (logout / token revocation) ───────────────────────────────

BLOCKLIST_PREFIX = "blocklist:"


async def is_token_revoked(jti: str, redis: aioredis.Redis) -> bool:
    return await redis.exists(f"{BLOCKLIST_PREFIX}{jti}") == 1


async def revoke_token(jti: str, ttl_seconds: int, redis: aioredis.Redis) -> None:
    await redis.setex(f"{BLOCKLIST_PREFIX}{jti}", ttl_seconds, "1")


# ── Current user resolution ────────────────────────────────────────────────────

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(credentials.credentials)
        if payload.type != "access":
            raise credentials_exception
        user_id = uuid.UUID(payload.sub)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )
    return user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required.",
        )
    return current_user


# ── Convenience type aliases ───────────────────────────────────────────────────

CurrentUser = Annotated[User, Depends(get_current_user)]
SuperUser = Annotated[User, Depends(get_current_superuser)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
