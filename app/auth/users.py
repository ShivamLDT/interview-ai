"""
FastAPI Users configuration and user manager.
"""
from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.config import settings
from app.core.database import get_async_session


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    """Get the user database adapter."""
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    """
    User manager for handling user operations.
    
    Customize user lifecycle events here:
    - on_after_register: Called after user registration
    - on_after_forgot_password: Called after password reset request
    - on_after_request_verify: Called after verification request
    """
    
    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    async def on_after_register(
        self, user: User, request=None
    ) -> None:
        """Handle post-registration logic."""
        print(f"User {user.id} has registered.")
        # TODO: Send welcome email, create default resources, etc.

    async def on_after_forgot_password(
        self, user: User, token: str, request=None
    ) -> None:
        """Handle password reset request."""
        print(f"User {user.id} has requested password reset. Token: {token}")
        # TODO: Send password reset email with token

    async def on_after_request_verify(
        self, user: User, token: str, request=None
    ) -> None:
        """Handle email verification request."""
        print(f"Verification requested for user {user.id}. Token: {token}")
        # TODO: Send verification email with token


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    """Get the user manager instance."""
    yield UserManager(user_db)


# JWT Authentication Configuration
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    """Get JWT strategy for authentication."""
    return JWTStrategy(
        secret=settings.secret_key,
        lifetime_seconds=settings.access_token_expire_minutes * 60,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# FastAPI Users instance
fastapi_users = FastAPIUsers[User, UUID](
    get_user_manager,
    [auth_backend],
)

# Dependency shortcuts for protected routes
current_active_user = fastapi_users.current_user(active=True)
current_active_verified_user = fastapi_users.current_user(active=True, verified=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)

