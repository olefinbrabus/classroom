from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from classroom.repositories import get_or_404
from database.models import Assignment, Enrollment, Grade, Lesson, Submission, User
from enums import EnrollmentStatus


async def get_user_or_404(db: AsyncSession, user_id: int) -> User:
    return await get_or_404(db, User, user_id, "User not found")


async def list_users(
    db: AsyncSession,
    *,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[User]:
    query = select(User).order_by(User.id).offset(offset).limit(limit)

    if search:
        value = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(value),
                User.first_name.ilike(value),
                User.second_name.ilike(value),
                User.third_name.ilike(value),
            )
        )

    result = await db.execute(query)
    return list(result.scalars().all())


async def list_user_enrollments(
    db: AsyncSession,
    user_id: int,
    *,
    course_id: int | None = None,
) -> list[Enrollment]:
    query = (
        select(Enrollment)
        .where(
            Enrollment.user_id == user_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        .options(selectinload(Enrollment.course))
        .order_by(Enrollment.id)
    )
    if course_id is not None:
        query = query.where(Enrollment.course_id == course_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def list_user_submissions(
    db: AsyncSession,
    user_id: int,
    *,
    course_id: int | None = None,
) -> list[Submission]:
    query = (
        select(Submission)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .join(Lesson, Assignment.lesson_id == Lesson.id)
        .where(Submission.student_id == user_id)
        .options(
            selectinload(Submission.assignment)
            .selectinload(Assignment.lesson)
            .selectinload(Lesson.course),
            selectinload(Submission.grade).selectinload(Grade.grader),
        )
        .order_by(Submission.submitted_at.desc(), Submission.id.desc())
    )
    if course_id is not None:
        query = query.where(Lesson.course_id == course_id)

    result = await db.execute(query)
    return list(result.scalars().all())
