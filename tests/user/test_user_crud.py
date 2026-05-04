import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from classroom.crud import (
    create_assignment,
    create_course,
    create_lesson,
    create_submission,
    enroll_user,
    grade_submission,
)
from classroom.schemas import (
    AssignmentSchemaCreate,
    CourseSchemaCreate,
    EnrollmentSchemaCreate,
    GradeSchemaCreate,
    LessonSchemaCreate,
    SubmissionSchemaCreate,
)
from database.engine import BaseModel
from database.models import User
from enums import EnrollmentRole
from user.crud import (
    get_course_user_progress,
    get_user_lms_summary,
    get_users,
    update_current_user_profile,
)
from user.schemas import UserProfileUpdate


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


async def create_user(db, user_id: int, email: str, is_teacher: bool = False):
    user = User(
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
    db.add(user)
    return user


async def create_lms_progress(db):
    teacher = await create_user(db, 1, "teacher@example.com", is_teacher=True)
    student = await create_user(db, 2, "student@example.com")
    outsider = await create_user(db, 3, "outsider@example.com")
    await db.commit()

    course = await create_course(
        db=db,
        course_data=CourseSchemaCreate(title="Python LMS"),
        user=teacher,
    )
    await enroll_user(
        db=db,
        course_id=course.id,
        enrollment_data=EnrollmentSchemaCreate(
            user_id=student.id,
            role=EnrollmentRole.STUDENT,
        ),
        user=teacher,
    )
    lesson = await create_lesson(
        db=db,
        course_id=course.id,
        lesson_data=LessonSchemaCreate(title="Users", is_published=True),
        user=teacher,
    )
    assignment = await create_assignment(
        db=db,
        lesson_id=lesson.id,
        assignment_data=AssignmentSchemaCreate(
            title="Profile CRUD",
            max_score=10,
            is_published=True,
        ),
        user=teacher,
    )
    submission = await create_submission(
        db=db,
        assignment_id=assignment.id,
        student_id=student.id,
        submission_data=SubmissionSchemaCreate(text="Done"),
    )
    await grade_submission(
        db=db,
        submission_id=submission.id,
        grader_id=teacher.id,
        grade_data=GradeSchemaCreate(score=9, feedback="Solid"),
    )
    return teacher, student, outsider, course


def test_user_lms_summary_returns_courses_and_grades(tmp_path):
    async def scenario():
        engine, async_session_maker = await make_session(tmp_path)

        try:
            async with async_session_maker() as db:
                teacher, student, outsider, course = await create_lms_progress(db)

                summary = await get_user_lms_summary(
                    db=db,
                    user_id=student.id,
                    actor=student,
                )

                assert summary.user.id == student.id
                assert [item.course_id for item in summary.courses] == [course.id]
                assert summary.courses[0].role == EnrollmentRole.STUDENT
                assert len(summary.submissions) == 1
                assert summary.submissions[0].assignment_title == "Profile CRUD"
                assert summary.submissions[0].grade_score == 9

                with pytest.raises(HTTPException) as exc_info:
                    await get_user_lms_summary(
                        db=db,
                        user_id=student.id,
                        actor=outsider,
                    )
                assert exc_info.value.status_code == 403

                course_summary = await get_course_user_progress(
                    db=db,
                    course_id=course.id,
                    user_id=student.id,
                    actor=teacher,
                )
                assert [item.course_id for item in course_summary.courses] == [
                    course.id
                ]
        finally:
            await engine.dispose()

    run_async(scenario())


def test_user_profile_and_listing_respect_lms_access(tmp_path):
    async def scenario():
        engine, async_session_maker = await make_session(tmp_path)

        try:
            async with async_session_maker() as db:
                teacher = await create_user(db, 1, "teacher@example.com", True)
                student = await create_user(db, 2, "student@example.com")
                await db.commit()

                updated = await update_current_user_profile(
                    db=db,
                    user=student,
                    user_data=UserProfileUpdate(first_name="Updated"),
                )
                assert updated.first_name == "Updated"

                with pytest.raises(HTTPException) as exc_info:
                    await get_users(db=db, actor=student)
                assert exc_info.value.status_code == 403

                users = await get_users(db=db, actor=teacher, search="student")
                assert [item.id for item in users] == [student.id]
        finally:
            await engine.dispose()

    run_async(scenario())
