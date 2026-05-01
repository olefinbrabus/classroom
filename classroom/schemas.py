from typing import Optional

from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field

from user.schemas import UserRead
from enums import ClassMaterialsType


class IdConfigModelSchema(PydanticBaseModel):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ClassroomBaseSchema(PydanticBaseModel):
    name: str
    description: Optional[str] = None


class ClassroomSchemaRead(IdConfigModelSchema, ClassroomBaseSchema):
    pass


class ClassBaseSchema(PydanticBaseModel):
    name: str


class ClassSchemaCreate(ClassBaseSchema):
    users: list[int] = Field(default_factory=list)
    classrooms: list[int] = Field(default_factory=list)


class ClassSchemaUpdate(PydanticBaseModel):
    name: Optional[str] = None


class ClassUserLinkSchema(PydanticBaseModel):
    user_id: int


class ClassClassroomLinkSchema(PydanticBaseModel):
    classroom_id: int


class ClassSchemaRead(IdConfigModelSchema, ClassBaseSchema):
    users: list[UserRead] = Field(default_factory=list)
    classrooms: list[ClassroomSchemaRead] = Field(default_factory=list)


class ClassroomSchemaCreate(ClassroomBaseSchema):
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
