from typing import Optional

from fastapi_users import schemas
from pydantic import BaseModel as PydanticBaseModel, ConfigDict, EmailStr, Field

from enums import EnrollmentRole, EnrollmentStatus, SubmissionStatus


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
    first_name: str = Field(min_length=1, max_length=320)
    second_name: str = Field(min_length=1, max_length=320)
    third_name: str = Field(min_length=1, max_length=320)
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False
    is_teacher: Optional[bool] = False


class UserUpdate(schemas.BaseUserUpdate):
    password: str | None = None
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=320)
    second_name: str | None = Field(default=None, min_length=1, max_length=320)
    third_name: str | None = Field(default=None, min_length=1, max_length=320)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_teacher: Optional[bool] = None


class SuperUserCreate(UserCreate):
    is_superuser: bool = True
    is_verified: bool = True
    is_teacher: bool = True


class UserProfileUpdate(PydanticBaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=320)
    second_name: str | None = Field(default=None, min_length=1, max_length=320)
    third_name: str | None = Field(default=None, min_length=1, max_length=320)


class UserCourseSummary(PydanticBaseModel):
    course_id: int
    title: str
    role: EnrollmentRole
    status: EnrollmentStatus
    is_active: bool


class UserSubmissionSummary(PydanticBaseModel):
    submission_id: int
    assignment_id: int
    assignment_title: str
    course_id: int
    course_title: str
    status: SubmissionStatus
    submitted_at: str
    graded_at: str | None = None
    grade_score: float | None = None
    grade_feedback: str | None = None


class UserLmsSummary(PydanticBaseModel):
    user: UserRead
    courses: list[UserCourseSummary]
    submissions: list[UserSubmissionSummary]
