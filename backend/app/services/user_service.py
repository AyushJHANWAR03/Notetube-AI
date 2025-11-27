"""
User service for database operations.
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User as UserModel
from app.schemas.user import UserCreate, UserUpdate, User


class UserService:
    """Service for user-related database operations."""

    async def get_user_by_id(self, user_id: UUID, db: AsyncSession) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User's UUID
            db: Database session

        Returns:
            User object or None if not found
        """
        result = await db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()
        return User.model_validate(user) if user else None

    async def get_user_by_email(self, email: str, db: AsyncSession) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User's email address
            db: Database session

        Returns:
            User object or None if not found
        """
        result = await db.execute(
            select(UserModel).where(UserModel.email == email)
        )
        user = result.scalar_one_or_none()
        return User.model_validate(user) if user else None

    async def get_user_by_google_sub(self, google_sub: str, db: AsyncSession) -> Optional[User]:
        """
        Get user by Google subject ID.

        Args:
            google_sub: Google subject ID
            db: Database session

        Returns:
            User object or None if not found
        """
        result = await db.execute(
            select(UserModel).where(UserModel.google_sub == google_sub)
        )
        user = result.scalar_one_or_none()
        return User.model_validate(user) if user else None

    async def create_user(self, user_data: UserCreate, db: AsyncSession) -> User:
        """
        Create a new user.

        Args:
            user_data: User creation data
            db: Database session

        Returns:
            Created user object
        """
        db_user = UserModel(
            email=user_data.email,
            name=user_data.name,
            avatar_url=user_data.avatar_url,
            google_sub=user_data.google_sub
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return User.model_validate(db_user)

    async def update_user(self, user_id: UUID, user_data: UserUpdate, db: AsyncSession) -> Optional[User]:
        """
        Update user information.

        Args:
            user_id: User's UUID
            user_data: User update data
            db: Database session

        Returns:
            Updated user object or None if not found
        """
        result = await db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        if user_data.name is not None:
            user.name = user_data.name
        if user_data.avatar_url is not None:
            user.avatar_url = user_data.avatar_url

        await db.commit()
        await db.refresh(user)
        return User.model_validate(user)

    async def delete_user(self, user_id: UUID, db: AsyncSession) -> bool:
        """
        Delete a user.

        Args:
            user_id: User's UUID
            db: Database session

        Returns:
            True if deleted, False if not found
        """
        result = await db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return False

        await db.delete(user)
        await db.commit()
        return True
