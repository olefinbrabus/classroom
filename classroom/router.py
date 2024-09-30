from fastapi import APIRouter
from fastapi.params import Depends

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


@router.get("/get/")
def get():
    return {"hello": "world"}


@router.get("/get/{id}")
def get(id, user: User = Depends(current_user), ):
    return user.hashed_password
