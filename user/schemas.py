from typing import Optional, overload

from fastapi_users import schemas
from pydantic import EmailStr


class UserRead(schemas.BaseUser[int]):
    id: int
    email: EmailStr
    first_name: str
    second_name: str
    third_name: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    is_teacher:bool

    class Config:
        from_attributes = True


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
