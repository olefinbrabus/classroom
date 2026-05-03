import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from classroom.services import (
    is_course_teacher,
    require_student_enrollment,
    require_submission_editable,
    require_submission_owner,
)
from database.engine import BaseModel
from database.models import Course, Enrollment, Submission, User
from enums import EnrollmentRole, EnrollmentStatus, SubmissionStatus


def run_async(coro):
    return asyncio.run(coro)


async def make_session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")

    async with engine.begin() as connection:
        await connection.run_sync(BaseModel.metadata.create_all)

    async_session_maker = sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return engine, async_session_maker


def make_user(user_id: int, email: str, is_teacher: bool = False) -> User:
    return User(
        id=user_id,
        email=email,
        first_name="Test",
        second_name="User",
        third_name=str(user_id),
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        is_teacher=is_teacher,
    )


def test_service_helpers_resolve_course_roles(tmp_path):
    async def scenario():
        engine, async_session_maker = await make_session(tmp_path)

        try:
            async with async_session_maker() as db:
                global_teacher = make_user(1, "teacher@example.com", is_teacher=True)
                course_teacher = make_user(2, "course-teacher@example.com")
                student = make_user(3, "student@example.com")
                blocked_student = make_user(4, "blocked@example.com")
                course = Course(title="Python LMS")

                db.add_all(
                    [
                        global_teacher,
                        course_teacher,
                        student,
                        blocked_student,
                        course,
                    ]
                )
                await db.flush()
                db.add_all(
                    [
                        Enrollment(
                            course_id=course.id,
                            user_id=course_teacher.id,
                            role=EnrollmentRole.TEACHER,
                            status=EnrollmentStatus.ACTIVE,
                        ),
                        Enrollment(
                            course_id=course.id,
                            user_id=student.id,
                            role=EnrollmentRole.STUDENT,
                            status=EnrollmentStatus.ACTIVE,
                        ),
                        Enrollment(
                            course_id=course.id,
                            user_id=blocked_student.id,
                            role=EnrollmentRole.STUDENT,
                            status=EnrollmentStatus.BLOCKED,
                        ),
                    ]
                )
                await db.commit()

                assert await is_course_teacher(db, course.id, global_teacher) is True
                assert await is_course_teacher(db, course.id, course_teacher) is True
                assert await is_course_teacher(db, course.id, student) is False

                enrollment = await require_student_enrollment(
                    db,
                    course.id,
                    student.id,
                )
                assert enrollment.role == EnrollmentRole.STUDENT

                with pytest.raises(HTTPException) as exc_info:
                    await require_student_enrollment(db, course.id, blocked_student.id)
                assert exc_info.value.status_code == 403
        finally:
            await engine.dispose()

    run_async(scenario())


def test_submission_guards_check_owner_and_edit_state():
    owner = make_user(1, "owner@example.com")
    other_user = make_user(2, "other@example.com")
    submission = Submission(
        id=10,
        assignment_id=1,
        student_id=owner.id,
        status=SubmissionStatus.SUBMITTED,
    )

    require_submission_owner(submission, owner)
    require_submission_editable(submission)

    with pytest.raises(HTTPException) as owner_exc:
        require_submission_owner(submission, other_user)
    assert owner_exc.value.detail == "Submission owner required"

    submission.status = SubmissionStatus.GRADED
    with pytest.raises(HTTPException) as editable_exc:
        require_submission_editable(submission)
    assert editable_exc.value.detail == "Graded submission cannot be changed"
