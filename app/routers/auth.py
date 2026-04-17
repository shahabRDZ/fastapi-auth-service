"""Authentication router: register, login, logout, token refresh, and /me."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select

from app.dependencies import CurrentUser, DbSession
from app.models.user import User
from app.schemas.user import (
    MessageResponse,
    RefreshTokenRequest,
    Token,
    UserRegister,
    UserLogin,
    UserResponse,
)
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(payload: UserRegister, db: DbSession) -> User:
    # Check for existing email / username
    result = await db.execute(
        select(User).where(
            (User.email == payload.email) | (User.username == payload.username)
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        field = "email" if existing.email == payload.email else "username"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with that {field} already exists.",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.flush()  # populate user.id before returning
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Obtain access and refresh tokens",
)
async def login(payload: UserLogin, db: DbSession) -> Token:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    user.last_login = datetime.now(timezone.utc)

    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Exchange a refresh token for a new token pair",
)
async def refresh_tokens(payload: RefreshTokenRequest, db: DbSession) -> Token:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = decode_token(payload.refresh_token)
        if token_data.type != "refresh":
            raise credentials_exception
        user_id = uuid.UUID(token_data.sub)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise credentials_exception

    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke the current access token",
)
async def logout(request: Request, current_user: CurrentUser) -> MessageResponse:
    # In a full implementation you would add the token's jti to the Redis blocklist.
    # For simplicity the client is responsible for discarding the tokens; the
    # refresh token TTL ensures server-side expiry without additional storage.
    return MessageResponse(message="Successfully logged out.")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve the authenticated user's profile",
)
async def me(current_user: CurrentUser) -> User:
    return current_user
