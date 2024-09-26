from datetime import datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy.event import listens_for
from sqlalchemy import (
    Boolean,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Table,
    Column,
    LargeBinary,
    Enum,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import BaseModel
from enums import ClassMaterialsType


class User(SQLAlchemyBaseUserTable[int], BaseModel):
    __tablename__ = "classroom_user"

    email: Mapped[str] = mapped_column(
        String(length=320), index=True, nullable=False, unique=True
    )
    first_name: Mapped[str] = mapped_column(
        String(length=320), index=True, nullable=False
    )
    second_name: Mapped[str] = mapped_column(
        String(length=320), index=True, nullable=False
    )
    third_name: Mapped[str] = mapped_column(
        String(length=320), index=True, nullable=False
    )

    hashed_password: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_teacher: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class_to_classroom_table = Table(
    "class_classroom",
    BaseModel.metadata,
    Column("class_id", Integer, ForeignKey("class.id")),
    Column("classroom_id", Integer, ForeignKey("classroom.id")),
)

class_to_user_table = Table(
    "class_users",
    BaseModel.metadata,
    Column("class_id", Integer, ForeignKey("class.id")),
    Column("user_id", Integer, ForeignKey("classroom_user.id")),
)


class Class(BaseModel):
    __tablename__ = "class"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    users: Mapped[list[User]] = relationship(secondary=class_to_user_table)


class Classroom(BaseModel):
    __tablename__ = "classroom"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(1024), nullable=True)
    classes: Mapped[list[Class]] = relationship(secondary=class_to_classroom_table)


class Material(BaseModel):
    __tablename__ = "material"

    description: Mapped[str] = mapped_column(String(1024), nullable=True)
    classroom: Mapped[Classroom] = mapped_column(
        ForeignKey("classroom.id"), nullable=False, index=True
    )
    user: Mapped[User] = mapped_column(ForeignKey("classroom_user.id"), nullable=False)
    material_type = mapped_column(Enum(ClassMaterialsType))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FileMaterial(BaseModel):
    __tablename__ = "file_material"

    file: Mapped[bytes] = mapped_column(LargeBinary)
    material: Mapped[Material] = mapped_column(
        ForeignKey("material.id"), nullable=False
    )


class CommentaryMaterial(BaseModel):
    __tablename__ = "commentary_material"

    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    material: Mapped[Material] = mapped_column(
        ForeignKey("material.id"), nullable=False
    )


class HomeWork(BaseModel):
    __tablename__ = "homework"

    evaluation: Mapped[int] = mapped_column(Integer, nullable=True)
    material: Mapped[Material] = mapped_column(
        ForeignKey("material.id"), nullable=False
    )
    user: Mapped[User] = mapped_column(ForeignKey("classroom_user.id"), nullable=False)


@listens_for(HomeWork, "before_insert")
def material_is_homework(mapper, connection, target: HomeWork):
    if target.material.material_type != ClassMaterialsType.HOMEWORK:
        raise TypeError("This material is not a homework")


class FileHomeWork(BaseModel):
    __tablename__ = "file_homework"

    file: Mapped[bytes] = mapped_column(LargeBinary)
    homework: Mapped[Material] = mapped_column(
        ForeignKey("homework.id"), nullable=False
    )
