from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from classroom.repositories import (
    commit_or_rollback,
    get_grade_for_submission,
    get_or_404,
    list_all_courses,
    list_assignment_submissions,
    list_course_enrollments,
    list_course_lessons,
    list_courses_for_user,
    list_lesson_assignments,
    list_lesson_materials,
)
from classroom.schemas import (
    AnnouncementSchemaCreate,
    AssignmentSchemaCreate,
    AssignmentSchemaUpdate,
    CourseSchemaCreate,
    CourseSchemaUpdate,
    EnrollmentSchemaCreate,
    EnrollmentSchemaUpdate,
    GradeSchemaCreate,
    LessonSchemaCreate,
    LessonSchemaUpdate,
    MaterialSchemaCreate,
    SubmissionSchemaCreate,
    SubmissionSchemaUpdate,
    UploadedFileSchemaCreate,
)
from classroom.services import (
    get_assignment_course_id,
    get_lesson_course_id,
    get_submission_course_id,
    is_course_teacher,
    is_global_teacher,
    require_assignment_published,
    require_course_access,
    require_course_teacher,
    require_grade_within_assignment_score,
    require_lesson_published_or_teacher,
    require_student_enrollment,
    require_submission_editable,
    require_submission_owner,
)
from database.models import (
    Announcement,
    Assignment,
    Course,
    Enrollment,
    Grade,
    Lesson,
    Material,
    Submission,
    UploadedFile,
    User,
)
from enums import EnrollmentRole, EnrollmentStatus, SubmissionStatus


course_options = (
    selectinload(Course.enrollments).selectinload(Enrollment.user),
    selectinload(Course.lessons),
)


async def get_user_or_404(db: AsyncSession, user_id: int) -> User:
    return await get_or_404(db, User, user_id, "User not found")


async def get_course_or_404(db: AsyncSession, course_id: int) -> Course:
    return await get_or_404(db, Course, course_id, "Course not found")


async def get_lesson_or_404(db: AsyncSession, lesson_id: int) -> Lesson:
    return await get_or_404(db, Lesson, lesson_id, "Lesson not found")


async def get_assignment_or_404(db: AsyncSession, assignment_id: int) -> Assignment:
    return await get_or_404(db, Assignment, assignment_id, "Assignment not found")


async def get_submission_or_404(db: AsyncSession, submission_id: int) -> Submission:
    return await get_or_404(db, Submission, submission_id, "Submission not found")


async def get_all_courses(db: AsyncSession, user: User):
    if is_global_teacher(user):
        return await list_all_courses(db)
    return await list_courses_for_user(db, user.id)


async def get_course(db: AsyncSession, course_id: int, user: User):
    await require_course_access(db=db, course_id=course_id, user=user)
    return await get_or_404(db, Course, course_id, "Course not found", course_options)


async def create_course(db: AsyncSession, course_data: CourseSchemaCreate, user: User):
    if not is_global_teacher(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required",
        )

    course = Course(**course_data.model_dump())
    db.add(course)
    db.add(
        Enrollment(
            course=course,
            user_id=user.id,
            role=EnrollmentRole.TEACHER,
            status=EnrollmentStatus.ACTIVE,
        )
    )
    await commit_or_rollback(db)
    await db.refresh(course)
    return course


async def update_course(
    db: AsyncSession,
    course_id: int,
    course_data: CourseSchemaUpdate,
    user: User,
):
    await require_course_teacher(db=db, course_id=course_id, user=user)
    course = await get_course_or_404(db=db, course_id=course_id)
    for field, value in course_data.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    await commit_or_rollback(db)
    await db.refresh(course)
    return course


async def delete_course(db: AsyncSession, course_id: int, user: User):
    await require_course_teacher(db=db, course_id=course_id, user=user)
    course = await get_course_or_404(db=db, course_id=course_id)
    await db.delete(course)
    await commit_or_rollback(db)
    return {"id": course_id, "deleted": True}


async def enroll_user(
    db: AsyncSession,
    course_id: int,
    enrollment_data: EnrollmentSchemaCreate,
    user: User,
):
    await require_course_teacher(db=db, course_id=course_id, user=user)
    course = await get_course_or_404(db=db, course_id=course_id)
    enrolled_user = await get_user_or_404(db=db, user_id=enrollment_data.user_id)
    enrollment = Enrollment(
        course=course,
        user=enrolled_user,
        role=enrollment_data.role,
        status=enrollment_data.status,
    )
    db.add(enrollment)
    await commit_or_rollback(db)
    await db.refresh(enrollment, attribute_names=["user"])
    return enrollment


async def get_course_enrollments(db: AsyncSession, course_id: int, user: User):
    await require_course_teacher(db=db, course_id=course_id, user=user)
    await get_course_or_404(db=db, course_id=course_id)
    return await list_course_enrollments(db, course_id)


async def update_enrollment(
    db: AsyncSession,
    enrollment_id: int,
    enrollment_data: EnrollmentSchemaUpdate,
    user: User,
):
    enrollment = await get_or_404(
        db,
        Enrollment,
        enrollment_id,
        "Enrollment not found",
        (selectinload(Enrollment.user),),
    )
    await require_course_teacher(db=db, course_id=enrollment.course_id, user=user)
    for field, value in enrollment_data.model_dump(exclude_unset=True).items():
        setattr(enrollment, field, value)
    await commit_or_rollback(db)
    await db.refresh(enrollment, attribute_names=["user"])
    return enrollment


async def create_lesson(
    db: AsyncSession,
    course_id: int,
    lesson_data: LessonSchemaCreate,
    user: User,
):
    await require_course_teacher(db=db, course_id=course_id, user=user)
    await get_course_or_404(db=db, course_id=course_id)
    lesson = Lesson(course_id=course_id, **lesson_data.model_dump())
    db.add(lesson)
    await commit_or_rollback(db)
    await db.refresh(lesson)
    return lesson


async def get_course_lessons(db: AsyncSession, course_id: int, user: User):
    await require_course_access(db=db, course_id=course_id, user=user)
    await get_course_or_404(db=db, course_id=course_id)
    only_published = not await is_course_teacher(
        db=db,
        course_id=course_id,
        user=user,
    )
    return await list_course_lessons(
        db,
        course_id,
        only_published=only_published,
    )


async def get_lesson(db: AsyncSession, lesson_id: int, user: User):
    lesson = await get_lesson_or_404(db=db, lesson_id=lesson_id)
    await require_course_access(db=db, course_id=lesson.course_id, user=user)
    require_lesson_published_or_teacher(
        lesson,
        await is_course_teacher(db=db, course_id=lesson.course_id, user=user),
    )
    return lesson


async def delete_lesson(db: AsyncSession, lesson_id: int, user: User):
    lesson = await get_lesson_or_404(db=db, lesson_id=lesson_id)
    await require_course_teacher(db=db, course_id=lesson.course_id, user=user)
    await db.delete(lesson)
    await commit_or_rollback(db)
    return {"id": lesson_id, "deleted": True}


async def get_lesson_materials(db: AsyncSession, lesson_id: int, user: User):
    course_id = await get_lesson_course_id(db=db, lesson_id=lesson_id)
    await require_course_access(db=db, course_id=course_id, user=user)
    return await list_lesson_materials(db, lesson_id)


async def update_lesson(
    db: AsyncSession,
    lesson_id: int,
    lesson_data: LessonSchemaUpdate,
    user: User,
):
    lesson = await get_lesson_or_404(db=db, lesson_id=lesson_id)
    await require_course_teacher(db=db, course_id=lesson.course_id, user=user)
    for field, value in lesson_data.model_dump(exclude_unset=True).items():
        setattr(lesson, field, value)
    await commit_or_rollback(db)
    await db.refresh(lesson)
    return lesson


async def create_material(
    db: AsyncSession,
    author_id: int,
    material_data: MaterialSchemaCreate,
    user: User,
):
    await get_user_or_404(db=db, user_id=author_id)
    course_id = await get_lesson_course_id(db=db, lesson_id=material_data.lesson_id)
    await require_course_teacher(db=db, course_id=course_id, user=user)
    material = Material(user_id=author_id, **material_data.model_dump())
    db.add(material)
    await commit_or_rollback(db)
    await db.refresh(material)
    return material


async def create_assignment(
    db: AsyncSession,
    lesson_id: int,
    assignment_data: AssignmentSchemaCreate,
    user: User,
):
    course_id = await get_lesson_course_id(db=db, lesson_id=lesson_id)
    await require_course_teacher(db=db, course_id=course_id, user=user)
    assignment = Assignment(lesson_id=lesson_id, **assignment_data.model_dump())
    db.add(assignment)
    await commit_or_rollback(db)
    await db.refresh(assignment)
    return assignment


async def update_assignment(
    db: AsyncSession,
    assignment_id: int,
    assignment_data: AssignmentSchemaUpdate,
    user: User,
):
    assignment = await get_assignment_or_404(db=db, assignment_id=assignment_id)
    await require_course_teacher(
        db=db,
        course_id=await get_assignment_course_id(db=db, assignment_id=assignment_id),
        user=user,
    )
    for field, value in assignment_data.model_dump(exclude_unset=True).items():
        setattr(assignment, field, value)
    await commit_or_rollback(db)
    await db.refresh(assignment)
    return assignment


async def get_lesson_assignments(db: AsyncSession, lesson_id: int, user: User):
    course_id = await get_lesson_course_id(db=db, lesson_id=lesson_id)
    await require_course_access(db=db, course_id=course_id, user=user)
    only_published = not await is_course_teacher(
        db=db,
        course_id=course_id,
        user=user,
    )
    return await list_lesson_assignments(
        db,
        lesson_id,
        only_published=only_published,
    )


async def delete_assignment(db: AsyncSession, assignment_id: int, user: User):
    assignment = await get_assignment_or_404(db=db, assignment_id=assignment_id)
    await require_course_teacher(
        db=db,
        course_id=await get_assignment_course_id(db=db, assignment_id=assignment_id),
        user=user,
    )
    await db.delete(assignment)
    await commit_or_rollback(db)
    return {"id": assignment_id, "deleted": True}


async def create_submission(
    db: AsyncSession,
    assignment_id: int,
    student_id: int,
    submission_data: SubmissionSchemaCreate,
):
    course_id = await get_assignment_course_id(db=db, assignment_id=assignment_id)
    await require_student_enrollment(db, course_id, student_id)
    assignment = await get_assignment_or_404(db=db, assignment_id=assignment_id)
    require_assignment_published(assignment)
    await get_user_or_404(db=db, user_id=student_id)
    submission = Submission(
        assignment_id=assignment_id,
        student_id=student_id,
        **submission_data.model_dump(),
    )
    db.add(submission)
    await commit_or_rollback(db)
    await db.refresh(submission)
    return submission


async def update_submission(
    db: AsyncSession,
    submission_id: int,
    submission_data: SubmissionSchemaUpdate,
    user: User,
):
    submission = await get_submission_or_404(db=db, submission_id=submission_id)
    require_submission_owner(submission, user)
    require_submission_editable(submission)
    for field, value in submission_data.model_dump(exclude_unset=True).items():
        setattr(submission, field, value)
    await commit_or_rollback(db)
    await db.refresh(submission)
    return submission


async def grade_submission(
    db: AsyncSession,
    submission_id: int,
    grader_id: int,
    grade_data: GradeSchemaCreate,
):
    course_id = await get_submission_course_id(db=db, submission_id=submission_id)
    grader = await get_user_or_404(db=db, user_id=grader_id)
    await require_course_teacher(db=db, course_id=course_id, user=grader)
    submission = await get_submission_or_404(db=db, submission_id=submission_id)
    assignment = await get_assignment_or_404(
        db=db,
        assignment_id=submission.assignment_id,
    )
    require_grade_within_assignment_score(assignment, grade_data.score)
    grade = await get_grade_for_submission(db=db, submission_id=submission_id)
    if grade is None:
        grade = Grade(
            submission_id=submission_id,
            grader_id=grader_id,
            **grade_data.model_dump(),
        )
        db.add(grade)
    else:
        grade.grader_id = grader_id
        for field, value in grade_data.model_dump().items():
            setattr(grade, field, value)

    submission.status = SubmissionStatus.GRADED
    submission.graded_at = datetime.now(timezone.utc)
    await commit_or_rollback(db)
    await db.refresh(grade)
    return grade


async def get_assignment_submissions(
    db: AsyncSession,
    assignment_id: int,
    user: User,
):
    course_id = await get_assignment_course_id(db=db, assignment_id=assignment_id)
    await require_course_teacher(db=db, course_id=course_id, user=user)
    return await list_assignment_submissions(db, assignment_id)


async def create_uploaded_file(
    db: AsyncSession,
    owner_id: int,
    file_data: UploadedFileSchemaCreate,
):
    await get_user_or_404(db=db, user_id=owner_id)
    uploaded_file = UploadedFile(owner_id=owner_id, **file_data.model_dump())
    db.add(uploaded_file)
    await commit_or_rollback(db)
    await db.refresh(uploaded_file)
    return uploaded_file


async def create_announcement(
    db: AsyncSession,
    course_id: int,
    author_id: int,
    announcement_data: AnnouncementSchemaCreate,
    user: User,
):
    await require_course_teacher(db=db, course_id=course_id, user=user)
    await get_course_or_404(db=db, course_id=course_id)
    await get_user_or_404(db=db, user_id=author_id)
    announcement = Announcement(
        course_id=course_id,
        author_id=author_id,
        **announcement_data.model_dump(),
    )
    db.add(announcement)
    await commit_or_rollback(db)
    await db.refresh(announcement)
    return announcement
