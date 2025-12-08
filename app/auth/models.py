"""
User database model for FastAPI Users.
"""
from fastapi_users.db import SQLAlchemyBaseUserTableUUID

from app.core.database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """
    User model with UUID primary key.
    
    Inherits from SQLAlchemyBaseUserTableUUID which provides:
    - id: UUID primary key
    - email: unique email field
    - hashed_password: password hash
    - is_active: boolean for account status
    - is_superuser: boolean for admin privileges
    - is_verified: boolean for email verification status
    
    Add custom fields below if needed:
    # first_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # last_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    """
    pass

