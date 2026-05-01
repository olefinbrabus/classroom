import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from classroom.crud import (
    add_classroom_to_class,
    add_user_to_class,
    create_class,
    delete_class,
    get_class,
    remove_classroom_from_class,
    remove_user_from_class,
    update_class,
)
from classroom.schemas import ClassSchemaCreate, ClassSchemaUpdate
from database.engine import BaseModel
from database.models import (
    Class,
    Classroom,
    User,
    class_to_classroom_table,
    class_to_user_table,
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


async def create_user(db, user_id: int, email: str):
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
        is_teacher=False,
    )
    db.add(user)
    return user


async def create_classroom(db, classroom_id: int, name: str):
    classroom = Classroom(
        id=classroom_id,
        name=name,
        description=f"{name} description",
    )
    db.add(classroom)
    return classroom


async def count_table_rows(db, table):
    result = await db.execute(select(func.count()).select_from(table))
    return result.scalar_one()


def test_class_crud_handles_complex_user_and_classroom_links(tmp_path):
    async def scenario():
        engine, async_session_maker = await make_session(tmp_path)

        try:
            async with async_session_maker() as db:
                await create_user(db, 1, "student1@example.com")
                await create_user(db, 2, "student2@example.com")
                await create_classroom(db, 1, "Backend")
                await create_classroom(db, 2, "Frontend")
                await db.commit()

                created_class = await create_class(
                    db=db,
                    class_data=ClassSchemaCreate(
                        name="Python",
                        users=[1],
                        classrooms=[1],
                    ),
                )

                assert created_class["name"] == "Python"
                assert [user["id"] for user in created_class["users"]] == [1]
                assert [room["id"] for room in created_class["classrooms"]] == [1]

                class_id = created_class["id"]

                with_second_user = await add_user_to_class(
                    db=db,
                    class_id=class_id,
                    user_id=2,
                )
                assert sorted(user["id"] for user in with_second_user["users"]) == [
                    1,
                    2,
                ]

                duplicate_user_link = await add_user_to_class(
                    db=db,
                    class_id=class_id,
                    user_id=2,
                )
                assert sorted(user["id"] for user in duplicate_user_link["users"]) == [
                    1,
                    2,
                ]

                with_second_room = await add_classroom_to_class(
                    db=db,
                    class_id=class_id,
                    classroom_id=2,
                )
                assert sorted(
                    room["id"] for room in with_second_room["classrooms"]
                ) == [1, 2]

                duplicate_room_link = await add_classroom_to_class(
                    db=db,
                    class_id=class_id,
                    classroom_id=2,
                )
                assert sorted(
                    room["id"] for room in duplicate_room_link["classrooms"]
                ) == [1, 2]

                without_first_user = await remove_user_from_class(
                    db=db,
                    class_id=class_id,
                    user_id=1,
                )
                assert [user["id"] for user in without_first_user["users"]] == [2]

                without_first_room = await remove_classroom_from_class(
                    db=db,
                    class_id=class_id,
                    classroom_id=1,
                )
                assert [room["id"] for room in without_first_room["classrooms"]] == [
                    2,
                ]

                updated_class = await update_class(
                    db=db,
                    class_id=class_id,
                    class_data=ClassSchemaUpdate(name="Advanced Python"),
                )
                assert updated_class["name"] == "Advanced Python"
                assert [user["id"] for user in updated_class["users"]] == [2]
                assert [room["id"] for room in updated_class["classrooms"]] == [2]

                fetched_class = await get_class(db=db, class_id=class_id)
                assert fetched_class == updated_class

                assert await count_table_rows(db, class_to_user_table) == 1
                assert await count_table_rows(db, class_to_classroom_table) == 1

                deleted_class = await delete_class(db=db, class_id=class_id)
                assert deleted_class == {"id": class_id, "deleted": True}
                assert await count_table_rows(db, class_to_user_table) == 0
                assert await count_table_rows(db, class_to_classroom_table) == 0

                with pytest.raises(HTTPException) as exc_info:
                    await get_class(db=db, class_id=class_id)

                assert exc_info.value.status_code == 404
        finally:
            await engine.dispose()

    run_async(scenario())


def test_create_class_requires_existing_related_records(tmp_path):
    async def scenario():
        engine, async_session_maker = await make_session(tmp_path)

        try:
            async with async_session_maker() as db:
                with pytest.raises(HTTPException) as exc_info:
                    await create_class(
                        db=db,
                        class_data=ClassSchemaCreate(
                            name="Python",
                            users=[100],
                            classrooms=[],
                        ),
                    )

                assert exc_info.value.status_code == 404
                assert exc_info.value.detail == "User not found"

                class_count = await count_table_rows(db, Class.__table__)
                assert class_count == 0
        finally:
            await engine.dispose()

    run_async(scenario())
