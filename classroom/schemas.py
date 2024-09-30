from pydantic import BaseModel as PydanticBaseModel

from database.models import User
from enums import ClassMaterialsType


class IdConfigModelSchema:
    id: int

    class Config:
        from_attributes = True


class ClassBaseSchema(PydanticBaseModel):
    name: str
    users: list[int]


class ClassSchemaCreate(ClassBaseSchema, IdConfigModelSchema):
    users: list[User]


class ClassroomBaseSchema(PydanticBaseModel):
    name: str
    description: str


class ClassroomSchemaCreate(ClassroomBaseSchema, IdConfigModelSchema):
    pass


class FileMaterialBaseSchema(PydanticBaseModel):
    file: bytes


class FileMaterialSchemaCreate(FileMaterialBaseSchema, IdConfigModelSchema):
    pass


class MateriaBaseSchema(PydanticBaseModel):
    description: str
    material_type: ClassMaterialsType
    file_material: list[FileMaterialBaseSchema]


class MaterialSchemaCreate(MateriaBaseSchema, IdConfigModelSchema):
    pass


class CommentaryMaterialBaseSchema(PydanticBaseModel):
    description: str


class CommentaryMaterialSchemaCreate(CommentaryMaterialBaseSchema, IdConfigModelSchema):
    pass


class FileHomeWorkBaseSchema(PydanticBaseModel):
    file: bytes
    homework: int


class FileHomeWorkSchemaCreate(FileHomeWorkBaseSchema, IdConfigModelSchema):
    pass


class HomeWorkBaseSchema(PydanticBaseModel):
    material: int
    file_homework: list[FileHomeWorkSchemaCreate] = None


class HomeWorkSchemaCreate(HomeWorkBaseSchema, IdConfigModelSchema):
    pass
