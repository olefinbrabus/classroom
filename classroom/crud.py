from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from classroom.schemas import ClassSchemaCreate, ClassSchemaRead, ClassSchemaUpdate
from database.models import (
    User,
    Class,
    Classroom,
)


class_options = (
    selectinload(Class.users),
    selectinload(Class.classrooms),
)


def serialize_class(class_obj: Class) -> dict:
    return ClassSchemaRead.model_validate(class_obj).model_dump()


async def get_class_or_404(db: AsyncSession, class_id: int) -> Class:
    query = await db.execute(
        select(Class).where(Class.id == class_id).options(*class_options)
    )
    class_obj = query.scalar_one_or_none()
    if class_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )
    return class_obj


async def get_user_or_404(db: AsyncSession, user_id: int) -> User:
    query = await db.execute(select(User).where(User.id == user_id))
    user = query.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def get_classroom_or_404(db: AsyncSession, classroom_id: int) -> Classroom:
    query = await db.execute(select(Classroom).where(Classroom.id == classroom_id))
    classroom = query.scalar_one_or_none()
    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found",
        )
    return classroom


async def commit_class(db: AsyncSession, class_id: int) -> dict:
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise exc
    return serialize_class(await get_class_or_404(db=db, class_id=class_id))


async def get_all_classes(db: AsyncSession):
    query = await db.execute(select(Class).options(*class_options))
    classes = query.scalars().all()
    return [serialize_class(class_obj) for class_obj in classes]


async def get_class(db: AsyncSession, class_id: int):
    return serialize_class(await get_class_or_404(db=db, class_id=class_id))


async def create_class(db: AsyncSession, class_data: ClassSchemaCreate):
    class_dict = class_data.model_dump()
    users_id = class_dict.pop("users")
    classrooms_id = class_dict.pop("classrooms")
    db_class = Class(**class_dict)

    for user_id in users_id:
        user = await get_user_or_404(db=db, user_id=user_id)
        db_class.users.append(user)

    for classroom_id in classrooms_id:
        classroom = await get_classroom_or_404(db=db, classroom_id=classroom_id)
        db_class.classrooms.append(classroom)

    db.add(db_class)

    try:
        await db.commit()
        await db.refresh(db_class)
    except Exception as e:
        await db.rollback()
        raise e

    return serialize_class(await get_class_or_404(db=db, class_id=db_class.id))


async def update_class(db: AsyncSession, class_id: int, class_data: ClassSchemaUpdate):
    class_obj = await get_class_or_404(db=db, class_id=class_id)
    update_data = class_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(class_obj, field, value)

    return await commit_class(db=db, class_id=class_obj.id)


async def delete_class(db: AsyncSession, class_id: int):
    class_obj = await get_class_or_404(db=db, class_id=class_id)
    await db.delete(class_obj)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise exc

    return {"id": class_id, "deleted": True}


async def add_user_to_class(db: AsyncSession, class_id: int, user_id: int):
    class_obj = await get_class_or_404(db=db, class_id=class_id)
    user = await get_user_or_404(db=db, user_id=user_id)

    if all(existing_user.id != user.id for existing_user in class_obj.users):
        class_obj.users.append(user)

    return await commit_class(db=db, class_id=class_id)


async def remove_user_from_class(db: AsyncSession, class_id: int, user_id: int):
    class_obj = await get_class_or_404(db=db, class_id=class_id)
    await get_user_or_404(db=db, user_id=user_id)
    class_obj.users = [
        existing_user
        for existing_user in class_obj.users
        if existing_user.id != user_id
    ]

    return await commit_class(db=db, class_id=class_id)


async def add_classroom_to_class(db: AsyncSession, class_id: int, classroom_id: int):
    class_obj = await get_class_or_404(db=db, class_id=class_id)
    classroom = await get_classroom_or_404(db=db, classroom_id=classroom_id)

    if all(
        existing_classroom.id != classroom.id
        for existing_classroom in class_obj.classrooms
    ):
        class_obj.classrooms.append(classroom)

    return await commit_class(db=db, class_id=class_id)


async def remove_classroom_from_class(
    db: AsyncSession, class_id: int, classroom_id: int
):
    class_obj = await get_class_or_404(db=db, class_id=class_id)
    await get_classroom_or_404(db=db, classroom_id=classroom_id)
    class_obj.classrooms = [
        existing_classroom
        for existing_classroom in class_obj.classrooms
        if existing_classroom.id != classroom_id
    ]

    return await commit_class(db=db, class_id=class_id)
