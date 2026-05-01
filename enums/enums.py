from enum import StrEnum, auto


class ClassMaterialsType(StrEnum):
    HOMEWORK = auto()
    MESSAGE = auto()
    MATERIALS = auto()


class EnrollmentRole(StrEnum):
    STUDENT = auto()
    TEACHER = auto()
    ASSISTANT = auto()


class EnrollmentStatus(StrEnum):
    PENDING = auto()
    ACTIVE = auto()
    COMPLETED = auto()
    BLOCKED = auto()


class SubmissionStatus(StrEnum):
    DRAFT = auto()
    SUBMITTED = auto()
    LATE = auto()
    GRADED = auto()
    RETURNED = auto()
