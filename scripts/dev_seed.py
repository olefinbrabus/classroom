import argparse
import asyncio
from datetime import datetime, timezone

from sqlalchemy import text

from database.engine import BaseModel, async_session_maker, engine
from database.models import (
    Assignment,
    Course,
    Enrollment,
    Lesson,
    Submission,
    User,
)
from enums import EnrollmentRole, EnrollmentStatus, SubmissionStatus
from user.manager import UserManager


TEACHER_EMAIL = "admin@admin.com"
TEACHER_PASSWORD = "Administrate_12345"
STUDENT_EMAIL = "student@example.com"
STUDENT_PASSWORD = "Student_12345"
OUTSIDER_EMAIL = "outsider@example.com"
OUTSIDER_PASSWORD = "Outsider_12345"
ALEMBIC_HEAD = "20260501_remove_class"


def password_hash(password: str) -> str:
    return UserManager(None).password_helper.hash(password)


async def reset_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(BaseModel.metadata.drop_all)
        await connection.run_sync(BaseModel.metadata.create_all)
        await connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL)"
            )
        )
        await connection.execute(text("DELETE FROM alembic_version"))
        await connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"),
            {"version_num": ALEMBIC_HEAD},
        )


async def seed_database() -> None:
    async with async_session_maker() as db:
        teacher = User(
            id=1,
            email=TEACHER_EMAIL,
            first_name="Admin",
            second_name="Teacher",
            third_name="Seed",
            hashed_password=password_hash(TEACHER_PASSWORD),
            is_active=True,
            is_superuser=True,
            is_verified=True,
            is_teacher=True,
        )
        student = User(
            id=2,
            email=STUDENT_EMAIL,
            first_name="Student",
            second_name="Manual",
            third_name="Seed",
            hashed_password=password_hash(STUDENT_PASSWORD),
            is_active=True,
            is_superuser=False,
            is_verified=True,
            is_teacher=False,
        )
        outsider = User(
            id=3,
            email=OUTSIDER_EMAIL,
            first_name="Outsider",
            second_name="Manual",
            third_name="Seed",
            hashed_password=password_hash(OUTSIDER_PASSWORD),
            is_active=True,
            is_superuser=False,
            is_verified=True,
            is_teacher=False,
        )
        course = Course(
            id=1,
            title="Seeded LMS Course",
            description="Stable course for test_main.http",
            is_active=True,
        )
        teacher_enrollment = Enrollment(
            id=1,
            course_id=1,
            user_id=1,
            role=EnrollmentRole.TEACHER,
            status=EnrollmentStatus.ACTIVE,
        )
        student_enrollment = Enrollment(
            id=2,
            course_id=1,
            user_id=2,
            role=EnrollmentRole.STUDENT,
            status=EnrollmentStatus.ACTIVE,
        )
        published_lesson = Lesson(
            id=1,
            course_id=1,
            title="Seeded published lesson",
            description="Visible to enrolled students",
            position=1,
            is_published=True,
        )
        draft_lesson = Lesson(
            id=2,
            course_id=1,
            title="Seeded draft lesson",
            description="Visible to teachers only",
            position=0,
            is_published=False,
        )
        assignment = Assignment(
            id=1,
            lesson_id=1,
            title="Seeded assignment",
            description="Stable assignment for manual checks",
            max_score=10,
            is_published=True,
        )
        submission = Submission(
            id=1,
            assignment_id=1,
            student_id=2,
            text="Seeded student answer",
            status=SubmissionStatus.SUBMITTED,
            submitted_at=datetime.now(timezone.utc),
        )

        db.add_all(
            [
                teacher,
                student,
                outsider,
                course,
                teacher_enrollment,
                student_enrollment,
                published_lesson,
                draft_lesson,
                assignment,
                submission,
            ]
        )
        await db.commit()


async def run(reset: bool) -> None:
    if reset:
        await reset_database()
    else:
        async with engine.begin() as connection:
            await connection.run_sync(BaseModel.metadata.create_all)
    await seed_database()
    await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset and seed the local dev LMS database."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all model tables before seeding.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        asyncio.run(run(reset=args.reset))
    except Exception as exc:
        print(f"Dev seed failed: {exc}")
        print("Run with --reset when the database already contains seed data.")
        return 1

    print("Seeded dev database.")
    print(f"Teacher:  {TEACHER_EMAIL} / {TEACHER_PASSWORD}")
    print(f"Student:  {STUDENT_EMAIL} / {STUDENT_PASSWORD}")
    print(f"Outsider: {OUTSIDER_EMAIL} / {OUTSIDER_PASSWORD}")
    print("Stable ids: course=1, lesson=1, assignment=1, submission=1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
