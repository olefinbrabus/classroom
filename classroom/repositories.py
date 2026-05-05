from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Assignment, Course, Enrollment, Grade, Lesson, Material
from database.models import Submission
from enums import EnrollmentStatus


async def commit_or_rollback(db: AsyncSession) -> None:
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def get_or_404(db: AsyncSession, model, obj_id: int, detail: str, options=()):
    query = select(model).where(model.id == obj_id).options(*options)
    result = await db.execute(query)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return obj


async def list_courses_for_user(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Course)
        .join(Enrollment)
        .where(
            Enrollment.user_id == user_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        .order_by(Course.id)
    )
    return result.scalars().all()


async def list_all_courses(db: AsyncSession):
    result = await db.execute(select(Course).order_by(Course.id))
    return result.scalars().all()


async def list_course_enrollments(db: AsyncSession, course_id: int):
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.course_id == course_id)
        .options(selectinload(Enrollment.user))
        .order_by(Enrollment.id)
    )
    return result.scalars().all()


async def get_enrollment_by_course_user(
    db: AsyncSession,
    course_id: int,
    user_id: int,
) -> Enrollment | None:
    result = await db.execute(
        select(Enrollment)
        .where(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user_id,
        )
        .options(selectinload(Enrollment.user))
    )
    return result.scalar_one_or_none()


async def list_course_lessons(
    db: AsyncSession,
    course_id: int,
    *,
    only_published: bool,
):
    query = select(Lesson).where(Lesson.course_id == course_id)
    if only_published:
        query = query.where(Lesson.is_published.is_(True))
    result = await db.execute(query.order_by(Lesson.position, Lesson.id))
    return result.scalars().all()


async def list_lesson_materials(db: AsyncSession, lesson_id: int):
    result = await db.execute(
        select(Material).where(Material.lesson_id == lesson_id).order_by(Material.id)
    )
    return result.scalars().all()


async def list_lesson_assignments(
    db: AsyncSession,
    lesson_id: int,
    *,
    only_published: bool,
):
    query = select(Assignment).where(Assignment.lesson_id == lesson_id)
    if only_published:
        query = query.where(Assignment.is_published.is_(True))
    result = await db.execute(query.order_by(Assignment.id))
    return result.scalars().all()


async def list_assignment_submissions(db: AsyncSession, assignment_id: int):
    result = await db.execute(
        select(Submission)
        .where(Submission.assignment_id == assignment_id)
        .order_by(Submission.id)
    )
    return result.scalars().all()


async def get_submission_by_assignment_student(
    db: AsyncSession,
    assignment_id: int,
    student_id: int,
) -> Submission | None:
    result = await db.execute(
        select(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.student_id == student_id,
        )
    )
    return result.scalar_one_or_none()


async def get_grade_for_submission(
    db: AsyncSession,
    submission_id: int,
) -> Grade | None:
    result = await db.execute(select(Grade).where(Grade.submission_id == submission_id))
    return result.scalar_one_or_none()
