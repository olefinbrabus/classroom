from fastapi import APIRouter, Query

from dependencies import CurrentUser, DbSession
from user.crud import (
    get_course_user_progress,
    get_shared_course_user,
    get_user,
    get_user_lms_summary,
    get_users,
    update_current_user_profile,
)
from user.schemas import UserLmsSummary, UserProfileUpdate, UserRead

router = APIRouter()


@router.get("/me/", response_model=UserRead)
async def read_me(user: CurrentUser):
    return user


@router.patch("/me/", response_model=UserRead)
async def update_me(
    user_data: UserProfileUpdate,
    user: CurrentUser,
    db: DbSession,
):
    return await update_current_user_profile(db=db, user=user, user_data=user_data)


@router.get("/me/lms/", response_model=UserLmsSummary)
async def read_my_lms_summary(
    user: CurrentUser,
    db: DbSession,
):
    return await get_user_lms_summary(db=db, user_id=user.id, actor=user)


@router.get("/", response_model=list[UserRead])
async def read_users(
    user: CurrentUser,
    db: DbSession,
    search: str | None = Query(default=None, min_length=1, max_length=320),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return await get_users(
        db=db,
        actor=user,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/{user_id}/", response_model=UserRead)
async def read_user(
    user_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await get_user(db=db, user_id=user_id, actor=user)


@router.get("/{user_id}/lms/", response_model=UserLmsSummary)
async def read_user_lms_summary(
    user_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await get_user_lms_summary(db=db, user_id=user_id, actor=user)


@router.get(
    "/{user_id}/courses/{course_id}/",
    response_model=UserRead,
)
async def read_course_user(
    user_id: int,
    course_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await get_shared_course_user(
        db=db,
        course_id=course_id,
        user_id=user_id,
        actor=user,
    )


@router.get(
    "/{user_id}/courses/{course_id}/progress/",
    response_model=UserLmsSummary,
)
async def read_course_user_progress(
    user_id: int,
    course_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await get_course_user_progress(
        db=db,
        course_id=course_id,
        user_id=user_id,
        actor=user,
    )
