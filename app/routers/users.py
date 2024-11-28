"""Users router: list, retrieve, update, and deactivate users."""

import uuid
from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession, SuperUser
from app.models.user import User
from app.schemas.user import MessageResponse, PasswordChange, UserPublic, UserResponse, UserUpdate
from app.services.auth import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=List[UserPublic],
    summary="List users (superuser only)",
)
async def list_users(
    db: DbSession,
    _: SuperUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> List[User]:
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current user's full profile",
)
async def get_my_profile(current_user: CurrentUser) -> User:
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update the current user's profile",
)
async def update_my_profile(
    payload: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    if payload.username and payload.username != current_user.username:
        result = await db.execute(
            select(User).where(User.username == payload.username)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That username is already taken.",
            )
        current_user.username = payload.username

    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    return current_user


@router.post(
    "/me/change-password",
    response_model=MessageResponse,
    summary="Change the current user's password",
)
async def change_password(
    payload: PasswordChange,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    current_user.hashed_password = hash_password(payload.new_password)
    return MessageResponse(message="Password updated successfully.")


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    summary="Get a user by ID (superuser only)",
)
async def get_user(
    user_id: uuid.UUID,
    db: DbSession,
    _: SuperUser,
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Deactivate a user account (superuser only)",
)
async def deactivate_user(
    user_id: uuid.UUID,
    db: DbSession,
    current_superuser: SuperUser,
) -> MessageResponse:
    if user_id == current_superuser.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.is_active = False
    return MessageResponse(message=f"User {user_id} has been deactivated.")
