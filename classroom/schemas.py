from typing import Optional

from pydantic import BaseModel as PydanticBaseModel

from user.schemas import UserRead
from enums import ClassMaterialsType


class IdConfigModelSchema:
    id: int

    class Config:
        from_attributes = True



class ClassBaseSchema(PydanticBaseModel):
    name: str
    users: list[UserRead]


class ClassSchemaCreate(ClassBaseSchema):
    users: Optional[list[int]] = []

    class Config:
        from_attributes = True

class ClassSchemaRead(IdConfigModelSchema, ClassBaseSchema):
    pass

    class Config:
        from_attributes = True


class ClassroomBaseSchema(PydanticBaseModel):
    name: str
    description: str


class ClassroomSchemaCreate(IdConfigModelSchema, ClassroomBaseSchema):
    pass


class FileMaterialBaseSchema(PydanticBaseModel):
    file: bytes


class FileMaterialSchemaCreate(IdConfigModelSchema, FileMaterialBaseSchema):
    pass


class MateriaBaseSchema(PydanticBaseModel):
    description: str
    material_type: ClassMaterialsType
    file_material: list[FileMaterialBaseSchema]


class MaterialSchemaCreate(IdConfigModelSchema, MateriaBaseSchema):
    pass


class CommentaryMaterialBaseSchema(PydanticBaseModel):
    description: str


class CommentaryMaterialSchemaCreate(IdConfigModelSchema, CommentaryMaterialBaseSchema):
    pass


class FileHomeWorkBaseSchema(PydanticBaseModel):
    file: bytes
    homework: int


class FileHomeWorkSchemaCreate(IdConfigModelSchema, FileHomeWorkBaseSchema):
    pass


class HomeWorkBaseSchema(PydanticBaseModel):
    material: int
    file_homework: Optional[list[FileHomeWorkSchemaCreate]]


class HomeWorkSchemaCreate(IdConfigModelSchema, HomeWorkBaseSchema):
    pass
