from datetime import datetime

from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field

from enums import (
    ClassMaterialsType,
    EnrollmentRole,
    EnrollmentStatus,
    SubmissionStatus,
)
from user.schemas import UserRead


class IdConfigModelSchema(PydanticBaseModel):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CourseBaseSchema(PydanticBaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_active: bool = True


class CourseSchemaCreate(CourseBaseSchema):
    pass


class CourseSchemaUpdate(PydanticBaseModel):
    title: str | None = None
    description: str | None = None
    is_active: bool | None = None


class CourseSchemaRead(IdConfigModelSchema, CourseBaseSchema):
    created_at: datetime
    updated_at: datetime


class EnrollmentSchemaCreate(PydanticBaseModel):
    user_id: int = Field(gt=0)
    role: EnrollmentRole = EnrollmentRole.STUDENT
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE


class EnrollmentSchemaUpdate(PydanticBaseModel):
    role: EnrollmentRole | None = None
    status: EnrollmentStatus | None = None


class EnrollmentSchemaRead(IdConfigModelSchema):
    course_id: int
    user_id: int
    role: EnrollmentRole
    status: EnrollmentStatus
    created_at: datetime
    user: UserRead


class LessonBaseSchema(PydanticBaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    position: int = Field(default=0, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_published: bool = False


class LessonSchemaCreate(LessonBaseSchema):
    pass


class LessonSchemaUpdate(PydanticBaseModel):
    title: str | None = None
    description: str | None = None
    position: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_published: bool | None = None


class LessonSchemaRead(IdConfigModelSchema, LessonBaseSchema):
    course_id: int
    created_at: datetime


class MaterialBaseSchema(PydanticBaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    material_type: ClassMaterialsType
    lesson_id: int = Field(gt=0)


class MaterialSchemaCreate(MaterialBaseSchema):
    pass


class MaterialSchemaRead(IdConfigModelSchema, MaterialBaseSchema):
    user_id: int
    created_at: datetime
    updated_at: datetime | None = None


class AssignmentBaseSchema(PydanticBaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    deadline: datetime | None = None
    max_score: float = Field(default=100, gt=0)
    is_published: bool = False


class AssignmentSchemaCreate(AssignmentBaseSchema):
    pass


class AssignmentSchemaUpdate(PydanticBaseModel):
    title: str | None = None
    description: str | None = None
    deadline: datetime | None = None
    max_score: float | None = None
    is_published: bool | None = None


class AssignmentSchemaRead(IdConfigModelSchema, AssignmentBaseSchema):
    lesson_id: int
    created_at: datetime


class SubmissionSchemaCreate(PydanticBaseModel):
    text: str | None = None
    status: SubmissionStatus = SubmissionStatus.SUBMITTED


class SubmissionSchemaUpdate(PydanticBaseModel):
    text: str | None = None
    status: SubmissionStatus | None = None


class SubmissionSchemaRead(IdConfigModelSchema):
    assignment_id: int
    student_id: int
    text: str | None = None
    status: SubmissionStatus
    submitted_at: datetime
    graded_at: datetime | None = None


class GradeSchemaCreate(PydanticBaseModel):
    score: float = Field(ge=0)
    feedback: str | None = None


class GradeSchemaRead(IdConfigModelSchema):
    submission_id: int
    grader_id: int
    score: float
    feedback: str | None = None
    created_at: datetime


class UploadedFileSchemaCreate(PydanticBaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = None
    size: int = Field(default=0, ge=0)
    storage_path: str = Field(min_length=1, max_length=1024)
    content: str | None = None
    content_base64: str | None = None


class UploadedFileSchemaRead(IdConfigModelSchema):
    owner_id: int
    filename: str
    content_type: str | None = None
    size: int
    storage_path: str
    created_at: datetime


class AnnouncementSchemaCreate(PydanticBaseModel):
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)


class AnnouncementSchemaRead(IdConfigModelSchema, AnnouncementSchemaCreate):
    course_id: int
    author_id: int
    created_at: datetime


class FileMaterialBaseSchema(PydanticBaseModel):
    file: bytes


class FileMaterialSchemaCreate(IdConfigModelSchema, FileMaterialBaseSchema):
    pass


class CommentaryMaterialBaseSchema(PydanticBaseModel):
    description: str


class CommentaryMaterialSchemaCreate(IdConfigModelSchema, CommentaryMaterialBaseSchema):
    pass


class FileHomeWorkBaseSchema(PydanticBaseModel):
    file: bytes
    homework: int


class FileHomeWorkSchemaCreate(IdConfigModelSchema, FileHomeWorkBaseSchema):
    pass


class HomeWorkBaseSchema(PydanticBaseModel):
    material: int
    file_homework: list[FileHomeWorkSchemaCreate] | None = None


class HomeWorkSchemaCreate(IdConfigModelSchema, HomeWorkBaseSchema):
    pass
