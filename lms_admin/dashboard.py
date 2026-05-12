from datetime import datetime, timezone

from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates
from starlette_admin.views import CustomView

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

REVIEW_STATUSES = (SubmissionStatus.SUBMITTED, SubmissionStatus.LATE)


async def _scalar(session, statement, default=0):
    value = (await session.execute(statement)).scalar_one()
    return default if value is None else value


async def get_dashboard_data(session) -> dict:
    now = datetime.now(timezone.utc)

    submissions_to_review = await _scalar(
        session,
        select(func.count(Submission.id))
        .outerjoin(Grade, Grade.submission_id == Submission.id)
        .where(Submission.status.in_(REVIEW_STATUSES), Grade.id.is_(None)),
    )
    graded_submissions = await _scalar(session, select(func.count(Grade.id)))
    average_grade_percent = await _scalar(
        session,
        select(func.avg((Grade.score * 100.0) / Assignment.max_score))
        .select_from(Grade)
        .join(Submission, Submission.id == Grade.submission_id)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .where(Assignment.max_score > 0),
        default=None,
    )

    metrics = [
        {
            "label": "Active courses",
            "value": await _scalar(
                session,
                select(func.count(Course.id)).where(Course.is_active.is_(True)),
            ),
            "hint": "Published learning spaces",
            "icon": "fa fa-book",
            "url": "/admin/course/list",
        },
        {
            "label": "Students",
            "value": await _scalar(
                session,
                select(func.count(distinct(Enrollment.user_id))).where(
                    Enrollment.role == EnrollmentRole.STUDENT,
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                ),
            ),
            "hint": "Active enrollments",
            "icon": "fa fa-user-graduate",
            "url": "/admin/enrollment/list",
        },
        {
            "label": "Teachers",
            "value": await _scalar(
                session,
                select(func.count(User.id)).where(User.is_teacher.is_(True)),
            ),
            "hint": "Can manage courses",
            "icon": "fa fa-chalkboard-user",
            "url": "/admin/user/list",
        },
        {
            "label": "To review",
            "value": submissions_to_review,
            "hint": "Submitted work without a grade",
            "icon": "fa fa-inbox",
            "url": "/admin/submission/list",
            "tone": "warning" if submissions_to_review else "success",
        },
        {
            "label": "Published lessons",
            "value": await _scalar(
                session,
                select(func.count(Lesson.id)).where(Lesson.is_published.is_(True)),
            ),
            "hint": "Visible classwork",
            "icon": "fa fa-list-check",
            "url": "/admin/lesson/list",
        },
        {
            "label": "Resources",
            "value": await _scalar(session, select(func.count(Material.id))),
            "hint": "Materials and homework posts",
            "icon": "fa fa-file-lines",
            "url": "/admin/material/list",
        },
        {
            "label": "Average grade",
            "value": (
                "n/a"
                if average_grade_percent is None
                else f"{round(average_grade_percent)}%"
            ),
            "hint": f"{graded_submissions} graded submissions",
            "icon": "fa fa-star",
            "url": "/admin/grade/list",
        },
        {
            "label": "Files",
            "value": await _scalar(session, select(func.count(UploadedFile.id))),
            "hint": "Uploaded learning assets",
            "icon": "fa fa-upload",
            "url": "/admin/uploaded-file/list",
        },
    ]

    completion = await _submission_completion(session)
    to_review = await _assignments_to_review(session)
    upcoming = await _upcoming_assignments(session, now)
    course_health = await _course_health(session)
    recent_activity = await _recent_activity(session)

    return {
        "metrics": metrics,
        "completion": completion,
        "to_review": to_review,
        "upcoming": upcoming,
        "course_health": course_health,
        "recent_activity": recent_activity,
        "quick_actions": [
            {
                "label": "Create course",
                "url": "/admin/course/create",
                "icon": "fa fa-plus",
            },
            {
                "label": "Add lesson",
                "url": "/admin/lesson/create",
                "icon": "fa fa-list",
            },
            {
                "label": "Add assignment",
                "url": "/admin/assignment/create",
                "icon": "fa fa-clipboard",
            },
            {
                "label": "Upload file",
                "url": "/admin/uploaded-file/create",
                "icon": "fa fa-upload",
            },
            {
                "label": "Post announcement",
                "url": "/admin/announcement/create",
                "icon": "fa fa-bullhorn",
            },
            {
                "label": "Grade submissions",
                "url": "/admin/submission/list",
                "icon": "fa fa-check",
            },
        ],
    }


async def _submission_completion(session) -> dict:
    total_submissions = await _scalar(session, select(func.count(Submission.id)))
    graded = await _scalar(session, select(func.count(Grade.id)))
    returned = await _scalar(
        session,
        select(func.count(Submission.id)).where(
            Submission.status == SubmissionStatus.RETURNED
        ),
    )
    submitted = await _scalar(
        session,
        select(func.count(Submission.id)).where(
            Submission.status.in_(
                (
                    SubmissionStatus.SUBMITTED,
                    SubmissionStatus.LATE,
                    SubmissionStatus.GRADED,
                    SubmissionStatus.RETURNED,
                )
            )
        ),
    )
    draft = await _scalar(
        session,
        select(func.count(Submission.id)).where(Submission.status == SubmissionStatus.DRAFT),
    )
    completion_rate = 0 if total_submissions == 0 else round(submitted * 100 / total_submissions)
    graded_rate = 0 if total_submissions == 0 else round(graded * 100 / total_submissions)
    return {
        "total": total_submissions,
        "submitted": submitted,
        "draft": draft,
        "graded": graded,
        "returned": returned,
        "completion_rate": completion_rate,
        "graded_rate": graded_rate,
    }


async def _assignments_to_review(session) -> list[dict]:
    submitted_count = func.sum(
        case((Submission.status.in_(REVIEW_STATUSES), 1), else_=0)
    )
    ungraded_count = func.sum(
        case(
            (
                and_(Submission.status.in_(REVIEW_STATUSES), Grade.id.is_(None)),
                1,
            ),
            else_=0,
        )
    )
    statement = (
        select(
            Assignment.id,
            Assignment.title,
            Assignment.deadline,
            Lesson.title.label("lesson_title"),
            Course.title.label("course_title"),
            submitted_count.label("submitted_count"),
            ungraded_count.label("ungraded_count"),
        )
        .join(Lesson, Lesson.id == Assignment.lesson_id)
        .join(Course, Course.id == Lesson.course_id)
        .outerjoin(Submission, Submission.assignment_id == Assignment.id)
        .outerjoin(Grade, Grade.submission_id == Submission.id)
        .group_by(Assignment.id, Lesson.title, Course.title)
        .having(ungraded_count > 0)
        .order_by(ungraded_count.desc(), Assignment.deadline.asc())
        .limit(6)
    )
    rows = (await session.execute(statement)).all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "lesson": row.lesson_title,
            "course": row.course_title,
            "deadline": row.deadline,
            "submitted_count": row.submitted_count or 0,
            "ungraded_count": row.ungraded_count or 0,
            "url": f"/admin/assignment/detail/{row.id}",
        }
        for row in rows
    ]


async def _upcoming_assignments(session, now: datetime) -> list[dict]:
    statement = (
        select(Assignment)
        .options(selectinload(Assignment.lesson).selectinload(Lesson.course))
        .where(Assignment.deadline.is_not(None), Assignment.deadline >= now)
        .order_by(Assignment.deadline.asc())
        .limit(6)
    )
    assignments = (await session.execute(statement)).scalars().all()
    return [
        {
            "id": assignment.id,
            "title": assignment.title,
            "course": assignment.lesson.course.title,
            "lesson": assignment.lesson.title,
            "deadline": assignment.deadline,
            "url": f"/admin/assignment/detail/{assignment.id}",
        }
        for assignment in assignments
    ]


async def _course_health(session) -> list[dict]:
    courses = (
        await session.execute(select(Course).order_by(Course.is_active.desc(), Course.title).limit(8))
    ).scalars().all()
    rows = []
    for course in courses:
        lesson_count = await _scalar(
            session, select(func.count(Lesson.id)).where(Lesson.course_id == course.id)
        )
        published_lessons = await _scalar(
            session,
            select(func.count(Lesson.id)).where(
                Lesson.course_id == course.id,
                Lesson.is_published.is_(True),
            ),
        )
        assignment_count = await _scalar(
            session,
            select(func.count(Assignment.id))
            .join(Lesson, Lesson.id == Assignment.lesson_id)
            .where(Lesson.course_id == course.id),
        )
        student_count = await _scalar(
            session,
            select(func.count(distinct(Enrollment.user_id))).where(
                Enrollment.course_id == course.id,
                Enrollment.role == EnrollmentRole.STUDENT,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            ),
        )
        resource_count = await _scalar(
            session,
            select(func.count(Material.id))
            .join(Lesson, Lesson.id == Material.lesson_id)
            .where(Lesson.course_id == course.id),
        )
        to_review = await _scalar(
            session,
            select(func.count(Submission.id))
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .join(Lesson, Lesson.id == Assignment.lesson_id)
            .outerjoin(Grade, Grade.submission_id == Submission.id)
            .where(
                Lesson.course_id == course.id,
                Submission.status.in_(REVIEW_STATUSES),
                Grade.id.is_(None),
            ),
        )
        rows.append(
            {
                "id": course.id,
                "title": course.title,
                "is_active": course.is_active,
                "students": student_count,
                "lessons": lesson_count,
                "published_lessons": published_lessons,
                "assignments": assignment_count,
                "resources": resource_count,
                "to_review": to_review,
                "url": f"/admin/course/detail/{course.id}",
            }
        )
    return rows


async def _recent_activity(session) -> dict:
    announcements = (
        await session.execute(
            select(Announcement)
            .options(selectinload(Announcement.course), selectinload(Announcement.author))
            .order_by(Announcement.created_at.desc())
            .limit(5)
        )
    ).scalars().all()
    files = (
        await session.execute(
            select(UploadedFile)
            .options(selectinload(UploadedFile.owner))
            .order_by(UploadedFile.created_at.desc())
            .limit(5)
        )
    ).scalars().all()
    return {
        "announcements": [
            {
                "id": item.id,
                "title": item.title,
                "course": item.course.title if item.course else None,
                "author": item.author.email if item.author else None,
                "created_at": item.created_at,
                "url": f"/admin/announcement/detail/{item.id}",
            }
            for item in announcements
        ],
        "files": [
            {
                "id": item.id,
                "filename": item.filename,
                "owner": item.owner.email if item.owner else None,
                "size": item.size,
                "created_at": item.created_at,
                "url": f"/admin/uploaded-file/detail/{item.id}",
            }
            for item in files
        ],
    }


class DashboardView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Dashboard",
            icon="fa fa-chart-line",
            path="/",
            template_path="index.html",
            add_to_menu=False,
        )

    async def render(self, request: Request, templates: Jinja2Templates) -> Response:
        dashboard = await get_dashboard_data(request.state.session)
        return templates.TemplateResponse(
            request=request,
            name=self.template_path,
            context={
                "title": self.title(request),
                "dashboard": dashboard,
            },
        )
