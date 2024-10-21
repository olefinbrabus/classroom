from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from classroom.crud import get_all_classes, create_class
from classroom.schemas import ClassBaseSchema, ClassSchemaCreate
from database.engine import get_async_session
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
from settings import current_user

router = APIRouter()


@router.get("/")
def get():
    return {"hello": "world"}


@router.get("/classes/", response_model=list[ClassBaseSchema])
async def read_classes(user: User = Depends(current_user), db: AsyncSession = Depends(get_async_session)):
    return await get_all_classes(db=db)


@router.post("/classes/", response_model=ClassSchemaCreate)
async def create_class_post(class_data: ClassSchemaCreate, user: User = Depends(current_user),
                            db: AsyncSession = Depends(get_async_session)):
    return await create_class(class_data=class_data, db=db)
