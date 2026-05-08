from fastapi import APIRouter, File, UploadFile, status

from classroom.crud import (
    create_announcement,
    create_assignment,
    create_course,
    create_lesson,
    create_material,
    create_submission,
    create_uploaded_file,
    delete_course,
    delete_assignment,
    delete_lesson,
    enroll_user,
    get_all_courses,
    get_assignment_submissions,
    get_course,
    get_course_enrollments,
    get_course_lessons,
    get_lesson,
    get_lesson_assignments,
    get_lesson_materials,
    grade_submission,
    update_assignment,
    update_course,
    update_enrollment,
    update_lesson,
    update_submission,
)
from classroom.file_storage import save_upload_file
from classroom.schemas import (
    AnnouncementSchemaCreate,
    AnnouncementSchemaRead,
    AssignmentSchemaCreate,
    AssignmentSchemaRead,
    AssignmentSchemaUpdate,
    CourseSchemaCreate,
    CourseSchemaRead,
    CourseSchemaUpdate,
    EnrollmentSchemaCreate,
    EnrollmentSchemaRead,
    EnrollmentSchemaUpdate,
    GradeSchemaCreate,
    GradeSchemaRead,
    LessonSchemaCreate,
    LessonSchemaRead,
    LessonSchemaUpdate,
    MaterialSchemaCreate,
    MaterialSchemaRead,
    SubmissionSchemaCreate,
    SubmissionSchemaRead,
    SubmissionSchemaUpdate,
    UploadedFileSchemaCreate,
    UploadedFileSchemaRead,
)
from dependencies import CurrentUser, DbSession

router = APIRouter()


@router.get("/")
def get():
    return {"hello": "world"}


@router.get("/courses/", response_model=list[CourseSchemaRead])
async def read_courses(
    user: CurrentUser,
    db: DbSession,
):
    return await get_all_courses(db=db, user=user)


@router.post(
    "/courses/",
    response_model=CourseSchemaRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_course_post(
    course_data: CourseSchemaCreate,
    user: CurrentUser,
    db: DbSession,
):
    return await create_course(db=db, course_data=course_data, user=user)


@router.get("/courses/{course_id}/", response_model=CourseSchemaRead)
async def read_course(
    course_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await get_course(db=db, course_id=course_id, user=user)


@router.patch("/courses/{course_id}/", response_model=CourseSchemaRead)
async def update_course_patch(
    course_id: int,
    course_data: CourseSchemaUpdate,
    user: CurrentUser,
    db: DbSession,
):
    return await update_course(
        db=db,
        course_id=course_id,
        course_data=course_data,
        user=user,
    )


@router.delete(
    "/courses/{course_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_course_delete(
    course_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await delete_course(db=db, course_id=course_id, user=user)


@router.get(
    "/courses/{course_id}/enrollments/",
    response_model=list[EnrollmentSchemaRead],
)
async def read_course_enrollments(
    course_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await get_course_enrollments(db=db, course_id=course_id, user=user)


@router.post(
    "/courses/{course_id}/enrollments/",
    response_model=EnrollmentSchemaRead,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_user_post(
    course_id: int,
    enrollment_data: EnrollmentSchemaCreate,
    user: CurrentUser,
    db: DbSession,
):
    return await enroll_user(
        db=db,
        course_id=course_id,
        enrollment_data=enrollment_data,
        user=user,
    )


@router.patch("/enrollments/{enrollment_id}/", response_model=EnrollmentSchemaRead)
async def update_enrollment_patch(
    enrollment_id: int,
    enrollment_data: EnrollmentSchemaUpdate,
    user: CurrentUser,
    db: DbSession,
):
    return await update_enrollment(
        db=db,
        enrollment_id=enrollment_id,
        enrollment_data=enrollment_data,
        user=user,
    )


@router.get("/courses/{course_id}/lessons/", response_model=list[LessonSchemaRead])
async def read_course_lessons(
    course_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await get_course_lessons(db=db, course_id=course_id, user=user)


@router.post(
    "/courses/{course_id}/lessons/",
    response_model=LessonSchemaRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson_post(
    course_id: int,
    lesson_data: LessonSchemaCreate,
    user: CurrentUser,
    db: DbSession,
):
    return await create_lesson(
        db=db,
        course_id=course_id,
        lesson_data=lesson_data,
        user=user,
    )


@router.get("/lessons/{lesson_id}/", response_model=LessonSchemaRead)
async def read_lesson(
    lesson_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await get_lesson(db=db, lesson_id=lesson_id, user=user)


@router.patch("/lessons/{lesson_id}/", response_model=LessonSchemaRead)
async def update_lesson_patch(
    lesson_id: int,
    lesson_data: LessonSchemaUpdate,
    user: CurrentUser,
    db: DbSession,
):
    return await update_lesson(
        db=db,
        lesson_id=lesson_id,
        lesson_data=lesson_data,
        user=user,
    )


@router.delete(
    "/lessons/{lesson_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_lesson_delete(
    lesson_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await delete_lesson(db=db, lesson_id=lesson_id, user=user)


@router.get("/lessons/{lesson_id}/materials/", response_model=list[MaterialSchemaRead])
async def read_lesson_materials(
    lesson_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await get_lesson_materials(db=db, lesson_id=lesson_id, user=user)


@router.post(
    "/materials/",
    response_model=MaterialSchemaRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_material_post(
    material_data: MaterialSchemaCreate,
    user: CurrentUser,
    db: DbSession,
):
    return await create_material(
        db=db,
        author_id=user.id,
        material_data=material_data,
        user=user,
    )


@router.get(
    "/lessons/{lesson_id}/assignments/",
    response_model=list[AssignmentSchemaRead],
)
async def read_lesson_assignments(
    lesson_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await get_lesson_assignments(db=db, lesson_id=lesson_id, user=user)


@router.post(
    "/lessons/{lesson_id}/assignments/",
    response_model=AssignmentSchemaRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment_post(
    lesson_id: int,
    assignment_data: AssignmentSchemaCreate,
    user: CurrentUser,
    db: DbSession,
):
    return await create_assignment(
        db=db,
        lesson_id=lesson_id,
        assignment_data=assignment_data,
        user=user,
    )


@router.patch("/assignments/{assignment_id}/", response_model=AssignmentSchemaRead)
async def update_assignment_patch(
    assignment_id: int,
    assignment_data: AssignmentSchemaUpdate,
    user: CurrentUser,
    db: DbSession,
):
    return await update_assignment(
        db=db,
        assignment_id=assignment_id,
        assignment_data=assignment_data,
        user=user,
    )


@router.delete(
    "/assignments/{assignment_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_assignment_delete(
    assignment_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await delete_assignment(db=db, assignment_id=assignment_id, user=user)


@router.post(
    "/assignments/{assignment_id}/submissions/",
    response_model=SubmissionSchemaRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_submission_post(
    assignment_id: int,
    submission_data: SubmissionSchemaCreate,
    user: CurrentUser,
    db: DbSession,
):
    return await create_submission(
        db=db,
        assignment_id=assignment_id,
        student_id=user.id,
        submission_data=submission_data,
    )


@router.patch("/submissions/{submission_id}/", response_model=SubmissionSchemaRead)
async def update_submission_patch(
    submission_id: int,
    submission_data: SubmissionSchemaUpdate,
    user: CurrentUser,
    db: DbSession,
):
    return await update_submission(
        db=db,
        submission_id=submission_id,
        submission_data=submission_data,
        user=user,
    )


@router.get(
    "/assignments/{assignment_id}/submissions/",
    response_model=list[SubmissionSchemaRead],
)
async def read_assignment_submissions(
    assignment_id: int,
    user: CurrentUser,
    db: DbSession,
):
    return await get_assignment_submissions(
        db=db,
        assignment_id=assignment_id,
        user=user,
    )


@router.post("/submissions/{submission_id}/grade/", response_model=GradeSchemaRead)
async def grade_submission_post(
    submission_id: int,
    grade_data: GradeSchemaCreate,
    user: CurrentUser,
    db: DbSession,
):
    return await grade_submission(
        db=db,
        submission_id=submission_id,
        grader_id=user.id,
        grade_data=grade_data,
    )


@router.post(
    "/files/",
    response_model=UploadedFileSchemaRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_uploaded_file_post(
    file_data: UploadedFileSchemaCreate,
    user: CurrentUser,
    db: DbSession,
):
    return await create_uploaded_file(db=db, owner_id=user.id, file_data=file_data)


@router.post(
    "/files/upload/",
    response_model=UploadedFileSchemaRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file_post(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    storage_path, size = await save_upload_file(file=file, owner_id=user.id)
    file_data = UploadedFileSchemaCreate(
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        size=size,
        storage_path=storage_path,
    )
    return await create_uploaded_file(db=db, owner_id=user.id, file_data=file_data)


@router.post(
    "/courses/{course_id}/announcements/",
    response_model=AnnouncementSchemaRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_announcement_post(
    course_id: int,
    announcement_data: AnnouncementSchemaCreate,
    user: CurrentUser,
    db: DbSession,
):
    return await create_announcement(
        db=db,
        course_id=course_id,
        author_id=user.id,
        announcement_data=announcement_data,
        user=user,
    )
