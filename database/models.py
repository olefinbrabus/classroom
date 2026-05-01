from datetime import datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy.event import listens_for
from sqlalchemy import (
    Boolean,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    LargeBinary,
    Enum,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import BaseModel
from enums import (
    ClassMaterialsType,
    EnrollmentRole,
    EnrollmentStatus,
    SubmissionStatus,
)


class User(SQLAlchemyBaseUserTable[int], BaseModel):
    __tablename__ = "classroom_user"

    email: Mapped[str] = mapped_column(
        String(length=320), index=True, nullable=False, unique=True
    )
    first_name: Mapped[str] = mapped_column(
        String(length=320), index=True, nullable=False
    )
    second_name: Mapped[str] = mapped_column(
        String(length=320), index=True, nullable=False
    )
    third_name: Mapped[str] = mapped_column(
        String(length=320), index=True, nullable=False
    )

    hashed_password: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_teacher: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="user")
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="student",
        foreign_keys="Submission.student_id",
    )
    authored_announcements: Mapped[list["Announcement"]] = relationship(
        back_populates="author",
        foreign_keys="Announcement.author_id",
    )


class Course(BaseModel):
    __tablename__ = "course"

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Lesson.position",
    )
    announcements: Mapped[list["Announcement"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )


class Enrollment(BaseModel):
    __tablename__ = "enrollment"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_enrollment_course_user"),
    )

    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("classroom_user.id"),
        nullable=False,
    )
    role: Mapped[EnrollmentRole] = mapped_column(
        Enum(EnrollmentRole),
        default=EnrollmentRole.STUDENT,
        nullable=False,
    )
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus),
        default=EnrollmentStatus.ACTIVE,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    course: Mapped[Course] = relationship(back_populates="enrollments")
    user: Mapped[User] = relationship(back_populates="enrollments")


class Lesson(BaseModel):
    __tablename__ = "lesson"

    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    course: Mapped[Course] = relationship(back_populates="lessons")
    materials: Mapped[list["Material"]] = relationship(back_populates="lesson")
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
    )


class Material(BaseModel):
    __tablename__ = "material"

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    user_id: Mapped[int] = mapped_column(
        "user", ForeignKey("classroom_user.id"), nullable=False
    )
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lesson.id"), nullable=False)
    material_type: Mapped[ClassMaterialsType] = mapped_column(Enum(ClassMaterialsType))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    user: Mapped[User] = relationship()
    lesson: Mapped[Lesson] = relationship(back_populates="materials")


class FileMaterial(BaseModel):
    __tablename__ = "file_material"

    file: Mapped[bytes] = mapped_column(LargeBinary)
    material_id: Mapped[int] = mapped_column(
        "material", ForeignKey("material.id"), nullable=False
    )

    material: Mapped[Material] = relationship()


class CommentaryMaterial(BaseModel):
    __tablename__ = "commentary_material"

    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    material_id: Mapped[int] = mapped_column(
        "material", ForeignKey("material.id"), nullable=False
    )

    material: Mapped[Material] = relationship()


class Assignment(BaseModel):
    __tablename__ = "assignment"

    lesson_id: Mapped[int] = mapped_column(ForeignKey("lesson.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_score: Mapped[float] = mapped_column(Float, default=100, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lesson: Mapped[Lesson] = relationship(back_populates="assignments")
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class Submission(BaseModel):
    __tablename__ = "submission"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "student_id",
            name="uq_submission_assignment_student",
        ),
    )

    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignment.id"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("classroom_user.id"), nullable=False
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus),
        default=SubmissionStatus.SUBMITTED,
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assignment: Mapped[Assignment] = relationship(back_populates="submissions")
    student: Mapped[User] = relationship(
        back_populates="submissions",
        foreign_keys=[student_id],
    )
    grade: Mapped["Grade | None"] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class Grade(BaseModel):
    __tablename__ = "grade"
    __table_args__ = (UniqueConstraint("submission_id", name="uq_grade_submission"),)

    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submission.id"), nullable=False
    )
    grader_id: Mapped[int] = mapped_column(
        ForeignKey("classroom_user.id"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    submission: Mapped[Submission] = relationship(back_populates="grade")
    grader: Mapped[User] = relationship(foreign_keys=[grader_id])


class UploadedFile(BaseModel):
    __tablename__ = "uploaded_file"

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("classroom_user.id"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped[User] = relationship()


class Announcement(BaseModel):
    __tablename__ = "announcement"

    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("classroom_user.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    course: Mapped[Course] = relationship(back_populates="announcements")
    author: Mapped[User] = relationship(
        back_populates="authored_announcements",
        foreign_keys=[author_id],
    )


class HomeWork(BaseModel):
    __tablename__ = "homework"

    evaluation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    material_id: Mapped[int] = mapped_column(
        "material", ForeignKey("material.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        "user", ForeignKey("classroom_user.id"), nullable=False
    )

    material: Mapped[Material] = relationship()
    user: Mapped[User] = relationship()


@listens_for(HomeWork, "before_insert")
def material_is_homework(mapper, connection, target: HomeWork):
    if target.material.material_type != ClassMaterialsType.HOMEWORK:
        raise TypeError("This material is not a homework")


class FileHomeWork(BaseModel):
    __tablename__ = "file_homework"

    file: Mapped[bytes] = mapped_column(LargeBinary)
    homework_id: Mapped[int] = mapped_column(
        "homework", ForeignKey("homework.id"), nullable=False
    )

    homework: Mapped[HomeWork] = relationship()
