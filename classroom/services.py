from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Assignment, Enrollment, Grade, Lesson, Submission, User
from enums import EnrollmentRole, EnrollmentStatus, SubmissionStatus


def is_global_teacher(user: User) -> bool:
    return bool(user.is_superuser or user.is_teacher)


async def get_active_enrollment(
    db: AsyncSession,
    course_id: int,
    user_id: int,
) -> Enrollment | None:
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    return result.scalar_one_or_none()


async def is_course_teacher(db: AsyncSession, course_id: int, user: User) -> bool:
    if is_global_teacher(user):
        return True

    enrollment = await get_active_enrollment(db, course_id, user.id)
    return enrollment is not None and enrollment.role in (
        EnrollmentRole.TEACHER,
        EnrollmentRole.ASSISTANT,
    )


async def require_course_access(db: AsyncSession, course_id: int, user: User) -> None:
    if is_global_teacher(user):
        return

    if await get_active_enrollment(db, course_id, user.id) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Course access denied",
        )


async def require_course_teacher(db: AsyncSession, course_id: int, user: User) -> None:
    if not await is_course_teacher(db, course_id, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required",
        )


async def require_student_enrollment(
    db: AsyncSession,
    course_id: int,
    user_id: int,
) -> Enrollment:
    enrollment = await get_active_enrollment(db, course_id, user_id)
    if enrollment is None or enrollment.role != EnrollmentRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student enrollment required",
        )
    return enrollment


def require_submission_owner(submission: Submission, user: User) -> None:
    if submission.student_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Submission owner required",
        )


def require_submission_editable(submission: Submission) -> None:
    if submission.status == SubmissionStatus.GRADED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Graded submission cannot be changed",
        )


def require_lesson_published_or_teacher(
    lesson: Lesson,
    has_teacher_access: bool,
) -> None:
    if not lesson.is_published and not has_teacher_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lesson is not published",
        )


def require_assignment_published(assignment: Assignment) -> None:
    if not assignment.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignment is not published",
        )


async def get_lesson_course_id(db: AsyncSession, lesson_id: int) -> int:
    result = await db.execute(select(Lesson.course_id).where(Lesson.id == lesson_id))
    course_id = result.scalar_one_or_none()
    if course_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )
    return course_id


async def get_assignment_course_id(db: AsyncSession, assignment_id: int) -> int:
    result = await db.execute(
        select(Lesson.course_id)
        .join(Assignment, Assignment.lesson_id == Lesson.id)
        .where(Assignment.id == assignment_id)
    )
    course_id = result.scalar_one_or_none()
    if course_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return course_id


async def get_submission_course_id(db: AsyncSession, submission_id: int) -> int:
    result = await db.execute(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(selectinload(Submission.assignment).selectinload(Assignment.lesson))
    )
    submission = result.scalar_one_or_none()
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )
    return submission.assignment.lesson.course_id


async def get_grade_for_submission(
    db: AsyncSession,
    submission_id: int,
) -> Grade | None:
    result = await db.execute(
        select(Grade).where(Grade.submission_id == submission_id)
    )
    return result.scalar_one_or_none()
