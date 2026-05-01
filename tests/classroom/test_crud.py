import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from classroom.crud import (
    create_assignment,
    create_course,
    create_lesson,
    create_material,
    create_submission,
    enroll_user,
    get_all_courses,
    get_assignment_submissions,
    get_course_lessons,
    get_lesson_assignments,
    grade_submission,
    update_submission,
)
from classroom.schemas import (
    AssignmentSchemaCreate,
    CourseSchemaCreate,
    EnrollmentSchemaCreate,
    GradeSchemaCreate,
    LessonSchemaCreate,
    MaterialSchemaCreate,
    SubmissionSchemaCreate,
    SubmissionSchemaUpdate,
)
from database.engine import BaseModel
from database.models import User
from enums import (
    ClassMaterialsType,
    EnrollmentRole,
    SubmissionStatus,
)


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


async def create_course_with_people(db):
    teacher = await create_user(db, 1, "teacher@example.com", is_teacher=True)
    student = await create_user(db, 2, "student@example.com")
    outsider = await create_user(db, 3, "outsider@example.com")
    await db.commit()

    course = await create_course(
        db=db,
        course_data=CourseSchemaCreate(
            title="Python LMS",
            description="Async backend course",
        ),
        user=teacher,
    )
    await enroll_user(
        db=db,
        course_id=course["id"],
        enrollment_data=EnrollmentSchemaCreate(
            user_id=student.id,
            role=EnrollmentRole.STUDENT,
        ),
        user=teacher,
    )
    return teacher, student, outsider, course


def test_lms_flow_enforces_roles_and_published_content(tmp_path):
    async def scenario():
        engine, async_session_maker = await make_session(tmp_path)

        try:
            async with async_session_maker() as db:
                teacher, student, outsider, course = await create_course_with_people(db)

                hidden_lesson = await create_lesson(
                    db=db,
                    course_id=course["id"],
                    lesson_data=LessonSchemaCreate(
                        title="Draft lesson",
                        position=0,
                        is_published=False,
                    ),
                    user=teacher,
                )
                published_lesson = await create_lesson(
                    db=db,
                    course_id=course["id"],
                    lesson_data=LessonSchemaCreate(
                        title="Published lesson",
                        position=1,
                        is_published=True,
                    ),
                    user=teacher,
                )

                student_lessons = await get_course_lessons(
                    db=db,
                    course_id=course["id"],
                    user=student,
                )
                assert [lesson["id"] for lesson in student_lessons] == [
                    published_lesson["id"]
                ]

                with pytest.raises(HTTPException) as exc_info:
                    await get_course_lessons(
                        db=db,
                        course_id=course["id"],
                        user=outsider,
                    )
                assert exc_info.value.status_code == 403

                material = await create_material(
                    db=db,
                    author_id=teacher.id,
                    material_data=MaterialSchemaCreate(
                        title="Model guide",
                        description="Read before homework",
                        material_type=ClassMaterialsType.MATERIALS,
                        lesson_id=published_lesson["id"],
                    ),
                    user=teacher,
                )
                assert material["lesson_id"] == published_lesson["id"]

                hidden_assignment = await create_assignment(
                    db=db,
                    lesson_id=published_lesson["id"],
                    assignment_data=AssignmentSchemaCreate(
                        title="Hidden assignment",
                        is_published=False,
                    ),
                    user=teacher,
                )
                published_assignment = await create_assignment(
                    db=db,
                    lesson_id=published_lesson["id"],
                    assignment_data=AssignmentSchemaCreate(
                        title="Design LMS models",
                        max_score=12,
                        is_published=True,
                    ),
                    user=teacher,
                )

                student_assignments = await get_lesson_assignments(
                    db=db,
                    lesson_id=published_lesson["id"],
                    user=student,
                )
                assert [item["id"] for item in student_assignments] == [
                    published_assignment["id"]
                ]

                with pytest.raises(HTTPException) as exc_info:
                    await create_submission(
                        db=db,
                        assignment_id=hidden_assignment["id"],
                        student_id=student.id,
                        submission_data=SubmissionSchemaCreate(text="Too early"),
                    )
                assert exc_info.value.status_code == 403

                submission = await create_submission(
                    db=db,
                    assignment_id=published_assignment["id"],
                    student_id=student.id,
                    submission_data=SubmissionSchemaCreate(text="Done"),
                )
                assert submission["status"] == SubmissionStatus.SUBMITTED

                with pytest.raises(HTTPException) as exc_info:
                    await grade_submission(
                        db=db,
                        submission_id=submission["id"],
                        grader_id=student.id,
                        grade_data=GradeSchemaCreate(score=11),
                    )
                assert exc_info.value.status_code == 403

                grade = await grade_submission(
                    db=db,
                    submission_id=submission["id"],
                    grader_id=teacher.id,
                    grade_data=GradeSchemaCreate(score=11, feedback="Good work"),
                )
                assert grade["score"] == 11

                with pytest.raises(HTTPException) as exc_info:
                    await update_submission(
                        db=db,
                        submission_id=submission["id"],
                        submission_data=SubmissionSchemaUpdate(text="Changed"),
                        user=student,
                    )
                assert exc_info.value.detail == "Graded submission cannot be changed"

                submissions = await get_assignment_submissions(
                    db=db,
                    assignment_id=published_assignment["id"],
                    user=teacher,
                )
                assert [item["id"] for item in submissions] == [submission["id"]]

                teacher_lessons = await get_course_lessons(
                    db=db,
                    course_id=course["id"],
                    user=teacher,
                )
                assert [item["id"] for item in teacher_lessons] == [
                    hidden_lesson["id"],
                    published_lesson["id"],
                ]
        finally:
            await engine.dispose()

    run_async(scenario())


def test_course_listing_is_scoped_to_enrollment(tmp_path):
    async def scenario():
        engine, async_session_maker = await make_session(tmp_path)

        try:
            async with async_session_maker() as db:
                teacher, student, outsider, course = await create_course_with_people(db)

                student_courses = await get_all_courses(db=db, user=student)
                outsider_courses = await get_all_courses(db=db, user=outsider)
                teacher_courses = await get_all_courses(db=db, user=teacher)

                assert [item["id"] for item in student_courses] == [course["id"]]
                assert outsider_courses == []
                assert [item["id"] for item in teacher_courses] == [course["id"]]
        finally:
            await engine.dispose()

    run_async(scenario())
