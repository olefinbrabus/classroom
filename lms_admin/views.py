from starlette_admin.contrib.sqla import ModelView
from starlette_admin.exceptions import FormValidationError
from starlette_admin import RequestAction
from starlette_admin.fields import (
    BooleanField,
    DateTimeField,
    EmailField,
    EnumField,
    FileField,
    FloatField,
    HasOne,
    IntegerField,
    StringField,
    TextAreaField,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from classroom.file_storage import save_upload_file
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
from enums import (
    ClassMaterialsType,
    EnrollmentRole,
    EnrollmentStatus,
    SubmissionStatus,
)
from lms_admin.file_preview import UploadedFilePreviewField


def _model_id(value):
    return getattr(value, "id", value)


def _is_missing(value):
    value = _model_id(value)
    return value is None or value == ""


def _upload_file_from_data(data):
    value = data.get("upload")
    if isinstance(value, tuple):
        return value[0]
    return value


class SafeModelView(ModelView):
    page_size = 25
    page_size_options = [25, 50, 100]
    required_fields = []

    async def validate(self, request, data) -> None:
        errors = {
            field: "This field is required"
            for field in self.required_fields
            if _is_missing(data.get(field))
        }
        if errors:
            raise FormValidationError(errors)
        return await super().validate(request, data)


class UserAdmin(SafeModelView):
    fields = [
        IntegerField("id", label="ID", read_only=True),
        EmailField("email", label="Email", required=True),
        StringField("second_name", label="Last name", required=True),
        StringField("first_name", label="First name", required=True),
        StringField("third_name", label="Middle name", required=True),
        BooleanField("is_teacher", label="Teacher"),
        BooleanField("is_superuser", label="Admin"),
        BooleanField("is_active", label="Active"),
        BooleanField("is_verified", label="Verified"),
    ]
    searchable_fields = ["email", "first_name", "second_name", "third_name"]
    exclude_fields_from_create = ["id"]

    def can_create(self, request) -> bool:
        return False

    def can_delete(self, request) -> bool:
        return False


class CourseAdmin(SafeModelView):
    fields = [
        IntegerField("id", label="ID", read_only=True),
        StringField(
            "title",
            label="Course title",
            required=True,
            maxlength=255,
            help_text="Visible course name for teachers and students.",
        ),
        TextAreaField(
            "description",
            label="Course description",
            rows=5,
            help_text="Short overview, audience, goals, or grading policy.",
        ),
        BooleanField("is_active", label="Published"),
        DateTimeField("created_at", label="Created", read_only=True),
        DateTimeField("updated_at", label="Updated", read_only=True),
    ]
    searchable_fields = ["title", "description"]
    exclude_fields_from_create = ["id", "created_at", "updated_at"]
    exclude_fields_from_edit = ["id", "created_at", "updated_at"]


class EnrollmentAdmin(SafeModelView):
    fields = [
        IntegerField("id", label="ID", read_only=True),
        HasOne("course", label="Course", identity="course", required=True),
        HasOne("user", label="User", identity="user", required=True),
        EnumField("role", label="Role", required=True, enum=EnrollmentRole),
        EnumField("status", label="Status", required=True, enum=EnrollmentStatus),
        DateTimeField("created_at", label="Enrolled", read_only=True),
    ]
    required_fields = ["course", "user"]
    exclude_fields_from_create = ["id", "created_at"]
    exclude_fields_from_edit = ["id", "created_at"]

    async def before_create(self, request, data, obj) -> None:
        await self._ensure_unique_enrollment(
            request,
            course_id=_model_id(obj.course),
            user_id=_model_id(obj.user),
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
                {"user": "User is already enrolled in this course"}
            )


class LessonAdmin(SafeModelView):
    fields = [
        IntegerField("id", label="ID", read_only=True),
        HasOne("course", label="Course", identity="course", required=True),
        StringField("title", label="Lesson title", required=True, maxlength=255),
        TextAreaField(
            "description",
            label="Lesson description",
            rows=5,
            help_text="Intro, outcomes, links, or teacher notes for this lesson.",
        ),
        IntegerField(
            "position",
            label="Position",
            help_text="Lower numbers appear earlier in the course.",
        ),
        DateTimeField("starts_at", label="Available from"),
        DateTimeField("ends_at", label="Available until"),
        BooleanField("is_published", label="Published"),
        DateTimeField("created_at", label="Created", read_only=True),
    ]
    required_fields = ["course"]
    searchable_fields = ["title", "description"]
    exclude_fields_from_create = ["id", "created_at"]
    exclude_fields_from_edit = ["id", "created_at"]

    async def validate(self, request, data) -> None:
        errors = {}
        position = data.get("position")
        starts_at = data.get("starts_at")
        ends_at = data.get("ends_at")
        if position is not None and position < 0:
            errors["position"] = "Position must be zero or greater"
        if starts_at and ends_at and starts_at >= ends_at:
            errors["ends_at"] = "End date must be after the start date"
        if errors:
            raise FormValidationError(errors)
        return await super().validate(request, data)


class MaterialAdmin(SafeModelView):
    fields = [
        IntegerField("id", label="ID", read_only=True),
        HasOne("lesson", label="Lesson", identity="lesson", required=True),
        HasOne("user", label="Author", identity="user", required=True),
        StringField(
            "title",
            label="Resource title",
            required=True,
            maxlength=255,
            help_text="Name students will see in the lesson resource list.",
        ),
        TextAreaField(
            "description",
            label="Resource description",
            rows=5,
            help_text="Explain what students should read, watch, download, or do.",
        ),
        EnumField(
            "material_type",
            label="Resource type",
            required=True,
            enum=ClassMaterialsType,
        ),
        DateTimeField("created_at", label="Created", read_only=True),
        DateTimeField("updated_at", label="Updated", read_only=True),
    ]
    required_fields = ["user", "lesson", "title"]
    searchable_fields = ["title", "description"]
    exclude_fields_from_create = ["id", "created_at", "updated_at"]
    exclude_fields_from_edit = ["id", "created_at", "updated_at"]

    async def validate(self, request, data) -> None:
        if data.get("title") is not None:
            data["title"] = data["title"].strip()
        return await super().validate(request, data)


class AssignmentAdmin(SafeModelView):
    fields = [
        IntegerField("id", label="ID", read_only=True),
        HasOne("lesson", label="Lesson", identity="lesson", required=True),
        StringField("title", label="Assignment title", required=True, maxlength=255),
        TextAreaField(
            "description",
            label="Instructions",
            rows=8,
            help_text="Tell students what to submit and how it will be assessed.",
        ),
        DateTimeField("deadline", label="Due date"),
        FloatField("max_score", label="Max score", required=True),
        BooleanField("is_published", label="Published"),
        DateTimeField("created_at", label="Created", read_only=True),
    ]
    required_fields = ["lesson"]
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
        IntegerField("id", label="ID", read_only=True),
        HasOne("assignment", label="Assignment", identity="assignment", required=True),
        HasOne("student", label="Student", identity="user", required=True),
        TextAreaField("text", label="Online text submission", rows=8),
        EnumField("status", label="Status", required=True, enum=SubmissionStatus),
        DateTimeField("submitted_at", label="Submitted", read_only=True),
        DateTimeField("graded_at", label="Graded at"),
    ]
    required_fields = ["assignment", "student"]
    exclude_fields_from_create = ["id", "submitted_at", "graded_at"]
    exclude_fields_from_edit = ["id", "submitted_at"]

    async def before_create(self, request, data, obj) -> None:
        await self._ensure_unique_submission(
            request,
            assignment_id=_model_id(obj.assignment),
            student_id=_model_id(obj.student),
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
                {"student": "Submission already exists for this assignment"}
            )


class GradeAdmin(SafeModelView):
    fields = [
        IntegerField("id", label="ID", read_only=True),
        HasOne("submission", label="Submission", identity="submission", required=True),
        HasOne("grader", label="Grader", identity="user", required=True),
        FloatField("score", label="Score", required=True),
        TextAreaField("feedback", label="Feedback", rows=6),
        DateTimeField("created_at", label="Graded", read_only=True),
    ]
    required_fields = ["submission", "grader"]
    exclude_fields_from_create = ["id", "created_at"]
    exclude_fields_from_edit = ["id", "created_at"]

    async def validate(self, request, data) -> None:
        errors = {}
        score = data.get("score")
        submission_id = _model_id(data.get("submission"))
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
        IntegerField("id", label="ID", read_only=True),
        HasOne("owner", label="Owner", identity="user", required=True),
        FileField(
            "upload",
            label="Upload file",
            help_text="Select the file to store for course materials or assignment support.",
            exclude_from_list=True,
            exclude_from_detail=True,
        ),
        StringField(
            "filename",
            label="Filename",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        StringField(
            "content_type",
            label="Content type",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        IntegerField(
            "size",
            label="Size, bytes",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        StringField(
            "storage_path",
            label="Storage path",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        UploadedFilePreviewField(),
        DateTimeField(
            "created_at",
            label="Uploaded",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
    ]
    required_fields = ["owner"]
    searchable_fields = ["filename", "storage_path"]

    async def validate(self, request, data) -> None:
        errors = {}
        if _is_missing(data.get("owner")):
            errors["owner"] = "This field is required"
        if getattr(request.state, "action", None) == RequestAction.CREATE:
            upload = _upload_file_from_data(data)
            if upload is None:
                errors["upload"] = "Choose a file to upload"
        if errors:
            raise FormValidationError(errors)
        return await super().validate(request, data)

    async def before_create(self, request, data, obj) -> None:
        await self._apply_upload(data, obj)

    async def before_edit(self, request, data, obj) -> None:
        await self._apply_upload(data, obj)

    async def _apply_upload(self, data, obj) -> None:
        upload = _upload_file_from_data(data)
        if upload is None:
            return
        owner_id = _model_id(obj.owner)
        storage_path, size = await save_upload_file(upload, owner_id=owner_id)
        obj.filename = upload.filename or "upload.bin"
        obj.content_type = upload.content_type
        obj.size = size
        obj.storage_path = storage_path
        obj.content = None


class AnnouncementAdmin(SafeModelView):
    fields = [
        IntegerField("id", label="ID", read_only=True),
        HasOne("course", label="Course", identity="course", required=True),
        HasOne("author", label="Author", identity="user", required=True),
        StringField("title", label="Announcement title", required=True, maxlength=255),
        TextAreaField("message", label="Message", required=True, rows=8),
        DateTimeField("created_at", label="Published", read_only=True),
    ]
    required_fields = ["course", "author"]
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
