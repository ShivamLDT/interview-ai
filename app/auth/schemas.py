"""
User schemas for request/response validation.
"""
from uuid import UUID

from fastapi_users import schemas


class UserRead(schemas.BaseUser[UUID]):
    """
    Schema for reading user data.
    
    Inherits:
    - id: UUID
    - email: EmailStr
    - is_active: bool
    - is_superuser: bool
    - is_verified: bool
    
    Add custom fields here if you extended the User model:
    # first_name: str | None = None
    # last_name: str | None = None
    """
    pass


class UserCreate(schemas.BaseUserCreate):
    """
    Schema for creating a new user.
    
    Inherits:
    - email: EmailStr (required)
    - password: str (required)
    - is_active: bool | None = True
    - is_superuser: bool | None = False
    - is_verified: bool | None = False
    
    Add custom fields here if you extended the User model:
    # first_name: str | None = None
    # last_name: str | None = None
    """
    pass


class UserUpdate(schemas.BaseUserUpdate):
    """
    Schema for updating user data.
    
    Inherits:
    - password: str | None = None
    - email: EmailStr | None = None
    - is_active: bool | None = None
    - is_superuser: bool | None = None
    - is_verified: bool | None = None
    
    Add custom fields here if you extended the User model:
    # first_name: str | None = None
    # last_name: str | None = None
    """
    pass

