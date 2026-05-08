from starlette_admin.contrib.sqla import ModelView
from starlette_admin.exceptions import FormValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.models import (
    Announcement,
    Assignment,
    Course,
    Enrollment,
    Grade,
    Lesson,
    Material,
    Submission,
    UploadedFile,
    User,
)
from lms_admin.file_preview import UploadedFilePreviewField


def _model_id(value):
    return getattr(value, "id", value)


class SafeModelView(ModelView):
    page_size = 25
    page_size_options = [25, 50, 100]


class UserAdmin(SafeModelView):
    fields = [
        "id",
        "email",
        "first_name",
        "second_name",
        "third_name",
        "is_active",
        "is_superuser",
        "is_verified",
        "is_teacher",
    ]
    exclude_fields_from_create = ["id"]

    def can_create(self, request) -> bool:
        return False

    def can_delete(self, request) -> bool:
        return False


class CourseAdmin(SafeModelView):
    fields = ["id", "title", "description", "is_active", "created_at", "updated_at"]
    searchable_fields = ["title", "description"]
    exclude_fields_from_create = ["id", "created_at", "updated_at"]
    exclude_fields_from_edit = ["id", "created_at", "updated_at"]


class EnrollmentAdmin(SafeModelView):
    fields = ["id", "course_id", "user_id", "role", "status", "created_at"]
    exclude_fields_from_create = ["id", "created_at"]
    exclude_fields_from_edit = ["id", "created_at"]

    async def before_create(self, request, data, obj) -> None:
        await self._ensure_unique_enrollment(
            request,
            course_id=_model_id(obj.course_id),
            user_id=_model_id(obj.user_id),
        )

    async def _ensure_unique_enrollment(self, request, course_id: int, user_id: int):
        result = await request.state.session.execute(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.user_id == user_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            raise FormValidationError(
                {"user_id": "User is already enrolled in this course"}
            )


class LessonAdmin(SafeModelView):
    fields = [
        "id",
        "course_id",
        "title",
        "description",
        "position",
        "starts_at",
        "ends_at",
        "is_published",
        "created_at",
    ]
    searchable_fields = ["title", "description"]
    exclude_fields_from_create = ["id", "created_at"]
    exclude_fields_from_edit = ["id", "created_at"]


class MaterialAdmin(SafeModelView):
    fields = [
        "id",
        "title",
        "description",
        "user_id",
        "lesson_id",
        "material_type",
        "created_at",
        "updated_at",
    ]
    searchable_fields = ["title", "description"]
    exclude_fields_from_create = ["id", "created_at", "updated_at"]
    exclude_fields_from_edit = ["id", "created_at", "updated_at"]


class AssignmentAdmin(SafeModelView):
    fields = [
        "id",
        "lesson_id",
        "title",
        "description",
        "deadline",
        "max_score",
        "is_published",
        "created_at",
    ]
    searchable_fields = ["title", "description"]
    exclude_fields_from_create = ["id", "created_at"]
    exclude_fields_from_edit = ["id", "created_at"]

    async def validate(self, request, data) -> None:
        errors = {}
        if data.get("max_score") is not None and data["max_score"] <= 0:
            errors["max_score"] = "Max score must be greater than zero"
        if errors:
            raise FormValidationError(errors)
        return await super().validate(request, data)


class SubmissionAdmin(SafeModelView):
    fields = [
        "id",
        "assignment_id",
        "student_id",
        "text",
        "status",
        "submitted_at",
        "graded_at",
    ]
    exclude_fields_from_create = ["id", "submitted_at", "graded_at"]
    exclude_fields_from_edit = ["id", "submitted_at"]

    async def before_create(self, request, data, obj) -> None:
        await self._ensure_unique_submission(
            request,
            assignment_id=_model_id(obj.assignment_id),
            student_id=_model_id(obj.student_id),
        )

    async def _ensure_unique_submission(
        self,
        request,
        assignment_id: int,
        student_id: int,
    ):
        result = await request.state.session.execute(
            select(Submission).where(
                Submission.assignment_id == assignment_id,
                Submission.student_id == student_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            raise FormValidationError(
                {"student_id": "Submission already exists for this assignment"}
            )


class GradeAdmin(SafeModelView):
    fields = ["id", "submission_id", "grader_id", "score", "feedback", "created_at"]
    exclude_fields_from_create = ["id", "created_at"]
    exclude_fields_from_edit = ["id", "created_at"]

    async def validate(self, request, data) -> None:
        errors = {}
        score = data.get("score")
        submission_id = _model_id(data.get("submission_id"))
        if score is not None and score < 0:
            errors["score"] = "Score must be zero or greater"
        if score is not None and submission_id is not None:
            result = await request.state.session.execute(
                select(Submission)
                .where(Submission.id == submission_id)
                .options(selectinload(Submission.assignment))
            )
            submission = result.scalar_one_or_none()
            if submission and submission.assignment.max_score < score:
                errors["score"] = "Score cannot exceed assignment max score"
        if errors:
            raise FormValidationError(errors)
        return await super().validate(request, data)


class UploadedFileAdmin(SafeModelView):
    fields = [
        "id",
        "owner_id",
        "filename",
        "content_type",
        "size",
        "storage_path",
        UploadedFilePreviewField(),
        "created_at",
    ]
    searchable_fields = ["filename", "storage_path"]
    exclude_fields_from_create = ["id", "created_at"]
    exclude_fields_from_edit = ["id", "created_at"]


class AnnouncementAdmin(SafeModelView):
    fields = ["id", "course_id", "author_id", "title", "message", "created_at"]
    searchable_fields = ["title", "message"]
    exclude_fields_from_create = ["id", "created_at"]
    exclude_fields_from_edit = ["id", "created_at"]


ADMIN_VIEWS = [
    UserAdmin(User, icon="fa fa-users"),
    CourseAdmin(Course, icon="fa fa-book"),
    EnrollmentAdmin(Enrollment, icon="fa fa-user-plus"),
    LessonAdmin(Lesson, icon="fa fa-list"),
    MaterialAdmin(Material, icon="fa fa-file-lines"),
    AssignmentAdmin(Assignment, icon="fa fa-clipboard"),
    SubmissionAdmin(Submission, icon="fa fa-inbox"),
    GradeAdmin(Grade, icon="fa fa-star"),
    UploadedFileAdmin(UploadedFile, icon="fa fa-upload"),
    AnnouncementAdmin(Announcement, icon="fa fa-bullhorn"),
]
