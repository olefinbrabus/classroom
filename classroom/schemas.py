from pydantic import BaseModel as PydanticBaseModel

from enums import ClassMaterialsType

class IdModelSchema:
    id: int

    class Config:
        from_attributes = True


class ClassBaseSchema(PydanticBaseModel):
    name: str

class ClassCreateSchema(ClassBaseSchema, IdModelSchema):
    pass


class ClassroomBaseSchema(PydanticBaseModel):
    name: str
    description: str


class MateriaBaselSchema(PydanticBaseModel):
    description: str
    material_type: ClassMaterialsType


class FileMaterialBaseSchema(PydanticBaseModel):
    file: bytes


class CommentaryMaterialBaseSchema(PydanticBaseModel):
    description: str


class FileHomeWorkBaseSchema(PydanticBaseModel):
    file: bytes
    homework: int

class FileHomeWorkSchema(FileHomeWorkBaseSchema, IdModelSchema):
    pass


class HomeWorkBaseSchema(PydanticBaseModel):
    material: int
    file_homework: list[FileHomeWorkSchema]


