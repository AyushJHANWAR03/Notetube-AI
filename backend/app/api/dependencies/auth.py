"""
Authentication dependencies for FastAPI routes.
"""
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token
from app.schemas.user import User
from app.schemas.auth import TokenData
from app.services.user_service import UserService


security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Verify and decode token
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user_id from token
    user_id_str: Optional[str] = payload.get("user_id")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_service = UserService()
    user = await user_service.get_user_by_id(user_id, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current authenticated user if token is provided, otherwise None.

    Args:
        credentials: Optional HTTP Bearer token credentials
        db: Database session

    Returns:
        Current user object or None
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = verify_token(token)
        if payload is None:
            return None

        user_id_str: Optional[str] = payload.get("user_id")
        if user_id_str is None:
            return None

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            return None

        user_service = UserService()
        user = await user_service.get_user_by_id(user_id, db)
        return user
    except Exception:
        return None
