from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from classroom.schemas import ClassSchemaCreate, ClassSchemaRead
from database.models import (
    User,
    Class,
    Material,
    Classroom,
    ClassMaterialsType,
    HomeWork,
    FileHomeWork,
    CommentaryMaterial,
)


async def get_all_classes(db: AsyncSession):
    query = await db.execute(select(Class).options(selectinload(Class.users)))
    classes = query.scalars().all()
    result = [ ClassSchemaRead.from_orm(class_enum).model_dump() for class_enum in classes ]
    return result



async def create_class(db: AsyncSession, class_data: ClassSchemaCreate):
    class_dict = class_data.model_dump()
    copy_class_dict = class_dict.copy()
    users_id = class_dict.pop("users")
    db_class = Class(**class_dict)

    for user_id in users_id:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            db_class.users.append(user)

    db.add(db_class)

    try:
        await db.commit()
        await db.refresh(db_class)
    except Exception as e:
        await db.rollback()
        raise e

    return copy_class_dict
