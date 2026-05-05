import asyncio
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from database.engine import BaseModel, get_async_session
from database.models import User
from main import app
from settings import current_user


def run_async(coro):
    return asyncio.run(coro)


def assert_ok_json(response):
    assert response.status_code == 200
    return response.json()


async def make_session_maker(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/http.db")

    async with engine.begin() as connection:
        await connection.run_sync(BaseModel.metadata.create_all)

    async_session_maker = sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return engine, async_session_maker


async def seed_users(async_session_maker):
    async with async_session_maker() as db:
        teacher = User(
            id=1,
            email="teacher@example.com",
            first_name="Test",
            second_name="Teacher",
            third_name="User",
            hashed_password="hashed",
            is_active=True,
            is_superuser=False,
            is_verified=True,
            is_teacher=True,
        )
        student = User(
            id=2,
            email="student@example.com",
            first_name="Test",
            second_name="Student",
            third_name="User",
            hashed_password="hashed",
            is_active=True,
            is_superuser=False,
            is_verified=True,
            is_teacher=False,
        )
        outsider = User(
            id=3,
            email="outsider@example.com",
            first_name="Test",
            second_name="Outsider",
            third_name="User",
            hashed_password="hashed",
            is_active=True,
            is_superuser=False,
            is_verified=True,
            is_teacher=False,
        )
        db.add_all([teacher, student, outsider])
        await db.commit()
        return teacher, student, outsider


@contextmanager
def authenticated_client(user, async_session_maker):
    async def override_current_user():
        return user

    async def override_db_session():
        async with async_session_maker() as db:
            yield db

    app.dependency_overrides[current_user] = override_current_user
    app.dependency_overrides[get_async_session] = override_db_session

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_http_lms_cycle_creates_submits_grades_and_reads_user_summary(tmp_path):
    async def scenario():
        return await make_session_maker(tmp_path)

    engine, async_session_maker = run_async(scenario())
    teacher, student, _ = run_async(seed_users(async_session_maker))

    try:
        with authenticated_client(teacher, async_session_maker) as client:
            course = assert_ok_json(
                client.post(
                    "/classroom/courses/",
                    json={"title": "Python LMS", "description": "HTTP flow"},
                )
            )

            assert_ok_json(
                client.post(
                    f"/classroom/courses/{course['id']}/enrollments/",
                    json={
                        "user_id": student.id,
                        "role": "student",
                        "status": "active",
                    },
                )
            )
            duplicate_enrollment_response = client.post(
                f"/classroom/courses/{course['id']}/enrollments/",
                json={
                    "user_id": student.id,
                    "role": "student",
                    "status": "active",
                },
            )
            assert duplicate_enrollment_response.status_code == 409

            assert_ok_json(
                client.post(
                    f"/classroom/courses/{course['id']}/lessons/",
                    json={"title": "Draft lesson", "position": 0},
                )
            )

            published_lesson = assert_ok_json(
                client.post(
                    f"/classroom/courses/{course['id']}/lessons/",
                    json={
                        "title": "Published lesson",
                        "position": 1,
                        "is_published": True,
                    },
                )
            )

            assignment = assert_ok_json(
                client.post(
                    f"/classroom/lessons/{published_lesson['id']}/assignments/",
                    json={
                        "title": "Build user CRUD",
                        "max_score": 10,
                        "is_published": True,
                    },
                )
            )

        with authenticated_client(student, async_session_maker) as client:
            lessons_response = client.get(
                f"/classroom/courses/{course['id']}/lessons/",
            )
            assert lessons_response.status_code == 200
            assert [item["title"] for item in lessons_response.json()] == [
                "Published lesson"
            ]

            submission = assert_ok_json(
                client.post(
                    f"/classroom/assignments/{assignment['id']}/submissions/",
                    json={"text": "Done"},
                )
            )
            assert submission["student_id"] == student.id
            duplicate_submission_response = client.post(
                f"/classroom/assignments/{assignment['id']}/submissions/",
                json={"text": "Duplicate"},
            )
            assert duplicate_submission_response.status_code == 409

        with authenticated_client(teacher, async_session_maker) as client:
            submissions_response = client.get(
                f"/classroom/assignments/{assignment['id']}/submissions/",
            )
            assert submissions_response.status_code == 200
            assert [item["id"] for item in submissions_response.json()] == [
                submission["id"]
            ]

            grade = assert_ok_json(
                client.post(
                    f"/classroom/submissions/{submission['id']}/grade/",
                    json={"score": 9, "feedback": "Solid"},
                )
            )
            assert grade["score"] == 9

        with authenticated_client(student, async_session_maker) as client:
            summary = assert_ok_json(client.get("/users/me/lms/"))
            assert [item["course_id"] for item in summary["courses"]] == [course["id"]]
            assert summary["submissions"][0]["assignment_title"] == "Build user CRUD"
            assert summary["submissions"][0]["grade_score"] == 9
    finally:
        run_async(engine.dispose())


def test_http_lms_rejects_unauthorized_and_forbidden_actions(tmp_path):
    engine, async_session_maker = run_async(make_session_maker(tmp_path))
    teacher, student, outsider = run_async(seed_users(async_session_maker))

    try:
        app.dependency_overrides.clear()
        with TestClient(app) as client:
            assert client.get("/users/me/").status_code == 401
            assert client.get("/classroom/courses/").status_code == 401

        with authenticated_client(teacher, async_session_maker) as client:
            course = assert_ok_json(
                client.post(
                    "/classroom/courses/",
                    json={"title": "Permissions"},
                )
            )
            assert_ok_json(
                client.post(
                    f"/classroom/courses/{course['id']}/enrollments/",
                    json={
                        "user_id": student.id,
                        "role": "student",
                        "status": "active",
                    },
                )
            )
            lesson = assert_ok_json(
                client.post(
                    f"/classroom/courses/{course['id']}/lessons/",
                    json={"title": "Access", "is_published": True},
                )
            )
            assignment = assert_ok_json(
                client.post(
                    f"/classroom/lessons/{lesson['id']}/assignments/",
                    json={"title": "Forbidden actions", "is_published": True},
                )
            )

        with authenticated_client(student, async_session_maker) as client:
            create_lesson_response = client.post(
                f"/classroom/courses/{course['id']}/lessons/",
                json={"title": "Student lesson"},
            )
            assert create_lesson_response.status_code == 403

            submission = assert_ok_json(
                client.post(
                    f"/classroom/assignments/{assignment['id']}/submissions/",
                    json={"text": "Student answer"},
                )
            )

            grade_response = client.post(
                f"/classroom/submissions/{submission['id']}/grade/",
                json={"score": 8},
            )
            assert grade_response.status_code == 403

        with authenticated_client(outsider, async_session_maker) as client:
            lessons_response = client.get(
                f"/classroom/courses/{course['id']}/lessons/",
            )
            assert lessons_response.status_code == 403

            summary_response = client.get(f"/users/{student.id}/lms/")
            assert summary_response.status_code == 403

        with authenticated_client(teacher, async_session_maker) as client:
            progress_response = client.get(
                f"/users/{outsider.id}/courses/{course['id']}/progress/",
            )
            assert progress_response.status_code == 403
    finally:
        run_async(engine.dispose())


def test_http_register_creates_regular_student_user(tmp_path):
    engine, async_session_maker = run_async(make_session_maker(tmp_path))

    async def override_db_session():
        async with async_session_maker() as db:
            yield db

    app.dependency_overrides[get_async_session] = override_db_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/register/register",
                json={
                    "email": "student@example.com",
                    "password": "Student_12345",
                    "first_name": "Student",
                    "second_name": "Manual",
                    "third_name": "Check",
                },
            )

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "student@example.com"
        assert body["is_superuser"] is False
        assert body["is_teacher"] is False
    finally:
        app.dependency_overrides.clear()
        run_async(engine.dispose())
