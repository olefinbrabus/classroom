from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from classroom.repositories import commit_or_rollback
from classroom.services import (
    get_active_enrollment,
    is_global_teacher,
    require_course_teacher,
    require_student_enrollment,
)
from database.models import Enrollment, Submission, User
from user.repositories import (
    get_user_or_404,
    list_user_enrollments,
    list_user_submissions,
    list_users,
)
from user.schemas import (
    UserCourseSummary,
    UserLmsSummary,
    UserProfileUpdate,
    UserSubmissionSummary,
)


def _serialize_enrollment(enrollment: Enrollment) -> UserCourseSummary:
    return UserCourseSummary(
        course_id=enrollment.course_id,
        title=enrollment.course.title,
        role=enrollment.role,
        status=enrollment.status,
        is_active=enrollment.course.is_active,
    )


def _serialize_submission(submission: Submission) -> UserSubmissionSummary:
    assignment = submission.assignment
    course = assignment.lesson.course
    grade = submission.grade
    return UserSubmissionSummary(
        submission_id=submission.id,
        assignment_id=submission.assignment_id,
        assignment_title=assignment.title,
        course_id=course.id,
        course_title=course.title,
        status=submission.status,
        submitted_at=submission.submitted_at.isoformat(),
        graded_at=submission.graded_at.isoformat() if submission.graded_at else None,
        grade_score=grade.score if grade else None,
        grade_feedback=grade.feedback if grade else None,
    )


async def update_current_user_profile(
    db: AsyncSession,
    user: User,
    user_data: UserProfileUpdate,
) -> User:
    db_user = await get_user_or_404(db=db, user_id=user.id)
    for field, value in user_data.model_dump(exclude_unset=True).items():
        setattr(db_user, field, value)
    await commit_or_rollback(db)
    await db.refresh(db_user)
    return db_user


async def get_users(
    db: AsyncSession,
    actor: User,
    *,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[User]:
    if not is_global_teacher(actor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required",
        )
    return await list_users(db=db, search=search, limit=limit, offset=offset)


async def get_user(
    db: AsyncSession,
    user_id: int,
    actor: User,
) -> User:
    if actor.id != user_id and not is_global_teacher(actor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile access denied",
        )
    return await get_user_or_404(db=db, user_id=user_id)


async def get_user_lms_summary(
    db: AsyncSession,
    user_id: int,
    actor: User,
) -> UserLmsSummary:
    user = await get_user(db=db, user_id=user_id, actor=actor)
    enrollments = await list_user_enrollments(db=db, user_id=user_id)
    submissions = await list_user_submissions(db=db, user_id=user_id)
    return UserLmsSummary(
        user=user,
        courses=[_serialize_enrollment(item) for item in enrollments],
        submissions=[_serialize_submission(item) for item in submissions],
    )


async def get_course_user_progress(
    db: AsyncSession,
    course_id: int,
    user_id: int,
    actor: User,
) -> UserLmsSummary:
    await require_course_teacher(db=db, course_id=course_id, user=actor)
    await require_student_enrollment(db=db, course_id=course_id, user_id=user_id)
    user = await get_user_or_404(db=db, user_id=user_id)
    enrollments = await list_user_enrollments(
        db=db,
        user_id=user_id,
        course_id=course_id,
    )
    submissions = await list_user_submissions(
        db=db,
        user_id=user_id,
        course_id=course_id,
    )
    return UserLmsSummary(
        user=user,
        courses=[_serialize_enrollment(item) for item in enrollments],
        submissions=[_serialize_submission(item) for item in submissions],
    )


async def get_shared_course_user(
    db: AsyncSession,
    course_id: int,
    user_id: int,
    actor: User,
) -> User:
    await require_course_teacher(db=db, course_id=course_id, user=actor)
    if await get_active_enrollment(db=db, course_id=course_id, user_id=user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User enrollment not found",
        )
    return await get_user_or_404(db=db, user_id=user_id)
