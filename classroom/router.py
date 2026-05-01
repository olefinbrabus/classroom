from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from classroom.crud import (
    add_classroom_to_class,
    add_user_to_class,
    create_class,
    delete_class,
    get_all_classes,
    get_class,
    remove_classroom_from_class,
    remove_user_from_class,
    update_class,
)
from classroom.schemas import (
    ClassClassroomLinkSchema,
    ClassSchemaCreate,
    ClassSchemaRead,
    ClassSchemaUpdate,
    ClassUserLinkSchema,
)
from database.engine import get_async_session
from database.models import User
from settings import current_user

router = APIRouter()


@router.get("/")
def get():
    return {"hello": "world"}


@router.get("/classes/", response_model=list[ClassSchemaRead])
async def read_classes(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await get_all_classes(db=db)


@router.post("/classes/", response_model=ClassSchemaRead)
async def create_class_post(
    class_data: ClassSchemaCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await create_class(class_data=class_data, db=db)


@router.get("/classes/{class_id}/", response_model=ClassSchemaRead)
async def read_class(
    class_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await get_class(class_id=class_id, db=db)


@router.patch("/classes/{class_id}/", response_model=ClassSchemaRead)
async def update_class_patch(
    class_id: int,
    class_data: ClassSchemaUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await update_class(class_id=class_id, class_data=class_data, db=db)


@router.delete("/classes/{class_id}/")
async def delete_class_delete(
    class_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await delete_class(class_id=class_id, db=db)


@router.post("/classes/{class_id}/users/", response_model=ClassSchemaRead)
async def add_user_to_class_post(
    class_id: int,
    link_data: ClassUserLinkSchema,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await add_user_to_class(
        class_id=class_id,
        user_id=link_data.user_id,
        db=db,
    )


@router.delete("/classes/{class_id}/users/{user_id}/", response_model=ClassSchemaRead)
async def remove_user_from_class_delete(
    class_id: int,
    user_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await remove_user_from_class(
        class_id=class_id,
        user_id=user_id,
        db=db,
    )


@router.post("/classes/{class_id}/classrooms/", response_model=ClassSchemaRead)
async def add_classroom_to_class_post(
    class_id: int,
    link_data: ClassClassroomLinkSchema,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await add_classroom_to_class(
        class_id=class_id,
        classroom_id=link_data.classroom_id,
        db=db,
    )


@router.delete(
    "/classes/{class_id}/classrooms/{classroom_id}/",
    response_model=ClassSchemaRead,
)
async def remove_classroom_from_class_delete(
    class_id: int,
    classroom_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await remove_classroom_from_class(
        class_id=class_id,
        classroom_id=classroom_id,
        db=db,
    )
