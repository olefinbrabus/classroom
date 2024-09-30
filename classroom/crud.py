from sqlalchemy.orm import Session

from classroom.schemas import ClassBaseSchema
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

def get_all_classes(db: Session):
    return db.query(Class).all()

def create_class(db: Session, class_data: ClassBaseSchema):
    db_class = Class(**class_data.model_dump())
    db.add(db_class)
    db.commit()
    db.refresh(db_class)

    return db_class