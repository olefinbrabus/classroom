from typing import Optional

from fastapi_users import schemas
from pydantic import ConfigDict, EmailStr


class UserRead(schemas.BaseUser[int]):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str
    second_name: str
    third_name: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    is_teacher: bool


class UserCreate(schemas.BaseUserCreate):
    email: EmailStr
    password: str
    first_name: str
    second_name: str
    third_name: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False
    is_teacher: Optional[bool] = False


class UserUpdate(schemas.BaseUserUpdate):
    password: str
    email: EmailStr
    first_name: str
    second_name: str
    third_name: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False
    is_teacher: Optional[bool] = False


class SuperUserCreate(UserCreate):
    is_superuser: bool = True
    is_verified: bool = True
    is_teacher: bool = True
