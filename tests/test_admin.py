import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response
from starlette_admin.contrib.sqla import Admin
from starlette_admin.exceptions import FormValidationError, LoginFailed

from database.engine import BaseModel
from database.models import (
    Announcement,
    Assignment,
    Enrollment,
    Grade,
    Lesson,
    Material,
    Submission,
    UploadedFile,
    User,
)
from lms_admin.auth import SuperuserAdminAuth
from lms_admin.file_preview import add_uploaded_file_preview_route
from lms_admin.setup import ADMIN_TEMPLATES_DIR
from lms_admin.views import (
    AnnouncementAdmin,
    AssignmentAdmin,
    EnrollmentAdmin,
    GradeAdmin,
    LessonAdmin,
    MaterialAdmin,
    SubmissionAdmin,
    UploadedFileAdmin,
    UserAdmin,
)
from main import app
from user.auth import SECRET
from user.manager import UserManager


def run_async(coro):
    return asyncio.run(coro)


async def make_session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/admin.db")

    async with engine.begin() as connection:
        await connection.run_sync(BaseModel.metadata.create_all)

    async_session_maker = sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return engine, async_session_maker


async def seed_admin_users(db):
    password_hash = UserManager(None).password_helper.hash("Admin_12345")
    student_hash = UserManager(None).password_helper.hash("Student_12345")
    db.add_all(
        [
            User(
                id=1,
                email="admin@example.com",
                first_name="Admin",
                second_name="Root",
                third_name="User",
                hashed_password=password_hash,
                is_active=True,
                is_superuser=True,
                is_verified=True,
                is_teacher=True,
            ),
            User(
                id=2,
                email="student@example.com",
                first_name="Student",
                second_name="Regular",
                third_name="User",
                hashed_password=student_hash,
                is_active=True,
                is_superuser=False,
                is_verified=True,
                is_teacher=False,
            ),
        ]
    )
    await db.commit()


def make_admin_app(engine, views=None, include_file_preview_route=False):
    test_app = FastAPI()
    admin = Admin(
        engine,
        title="Test LMS Admin",
        base_url="/admin",
        templates_dir=str(ADMIN_TEMPLATES_DIR),
        auth_provider=SuperuserAdminAuth(),
        middlewares=[
            Middleware(
                SessionMiddleware,
                secret_key=SECRET,
                same_site="lax",
                https_only=False,
            )
        ],
    )
    for view in views or [UserAdmin(User)]:
        admin.add_view(view)
    if include_file_preview_route:
        add_uploaded_file_preview_route(admin)
    admin.mount_to(test_app)
    return test_app


def test_admin_routes_redirect_to_login_when_not_authenticated():
    client = TestClient(app, follow_redirects=False)

    response = client.get("/admin/")

    assert response.status_code == 303
    assert "/admin/login" in response.headers["location"]


def test_admin_login_accepts_only_active_superusers(tmp_path):
    async def scenario():
        engine, async_session_maker = await make_session(tmp_path)
        auth = SuperuserAdminAuth()

        try:
            async with async_session_maker() as db:
                await seed_admin_users(db)
                admin_request = SimpleNamespace(state=SimpleNamespace(session=db))
                admin_request.session = {}
                response = await auth.login(
                    "admin@example.com",
                    "Admin_12345",
                    False,
                    admin_request,
                    Response(),
                )

                assert response.status_code == 200
                assert admin_request.session[auth.session_key] == 1
                assert await auth.is_authenticated(admin_request) is True

                student_request = SimpleNamespace(state=SimpleNamespace(session=db))
                student_request.session = {}
                with pytest.raises(LoginFailed):
                    await auth.login(
                        "student@example.com",
                        "Student_12345",
                        False,
                        student_request,
                        Response(),
                    )
                assert student_request.session == {}
        finally:
            await engine.dispose()

    run_async(scenario())


def test_authenticated_admin_can_open_user_list(tmp_path):
    async def scenario():
        engine, async_session_maker = await make_session(tmp_path)

        try:
            async with async_session_maker() as db:
                await seed_admin_users(db)

            client = TestClient(make_admin_app(engine), follow_redirects=False)
            login_response = client.post(
                "/admin/login",
                data={
                    "username": "admin@example.com",
                    "password": "Admin_12345",
                },
            )
            assert login_response.status_code == 303

            list_response = client.get("/admin/user/list")

            assert list_response.status_code == 200
            assert "admin@example.com" in list_response.text
        finally:
            await engine.dispose()

    run_async(scenario())


def test_admin_create_forms_include_required_relationship_fields():
    expected_relationship_fields = [
        (EnrollmentAdmin(Enrollment), {"course", "user"}),
        (LessonAdmin(Lesson), {"course"}),
        (MaterialAdmin(Material), {"user", "lesson"}),
        (AssignmentAdmin(Assignment), {"lesson"}),
        (SubmissionAdmin(Submission), {"assignment", "student"}),
        (GradeAdmin(Grade), {"submission", "grader"}),
        (UploadedFileAdmin(UploadedFile), {"owner"}),
        (AnnouncementAdmin(Announcement), {"course", "author"}),
    ]

    for view, expected_names in expected_relationship_fields:
        fields = {
            field.name: type(field).__name__
            for field in view.get_fields_list(None)
        }

        assert expected_names <= fields.keys()
        assert all(fields[name] == "HasOne" for name in expected_names)


def test_admin_validate_rejects_missing_required_relationships():
    async def scenario():
        view = MaterialAdmin(Material)

        with pytest.raises(FormValidationError) as exc_info:
            await view.validate(
                None,
                {
                    "title": "Test",
                    "description": "Test",
                    "material_type": "MATERIALS",
                    "user": None,
                    "lesson": None,
                },
            )

        assert exc_info.value.errors == {
            "user": "This field is required",
            "lesson": "This field is required",
        }

    run_async(scenario())


def test_authenticated_admin_can_upload_file_from_create_form(tmp_path, monkeypatch):
    monkeypatch.setenv("CLASSROOM_UPLOAD_ROOT", str(tmp_path / "uploads"))

    async def scenario():
        engine, async_session_maker = await make_session(tmp_path)

        try:
            async with async_session_maker() as db:
                await seed_admin_users(db)

            client = TestClient(
                make_admin_app(
                    engine,
                    views=[UserAdmin(User), UploadedFileAdmin(UploadedFile)],
                    include_file_preview_route=True,
                ),
                follow_redirects=False,
            )
            login_response = client.post(
                "/admin/login",
                data={
                    "username": "admin@example.com",
                    "password": "Admin_12345",
                },
            )
            assert login_response.status_code == 303

            create_response = client.post(
                "/admin/uploaded-file/create",
                data={"owner": "1"},
                files={
                    "upload": (
                        "lesson-notes.txt",
                        b"Lesson notes",
                        "text/plain",
                    )
                },
            )

            assert create_response.status_code == 303
            assert create_response.headers["location"].endswith(
                "/admin/uploaded-file/list"
            )

            async with async_session_maker() as db:
                uploaded_file = (
                    await db.execute(select(UploadedFile))
                ).scalar_one()

            assert uploaded_file.owner_id == 1
            assert uploaded_file.filename == "lesson-notes.txt"
            assert uploaded_file.content_type == "text/plain"
            assert uploaded_file.size == len(b"Lesson notes")
            assert (tmp_path / "uploads" / uploaded_file.storage_path).read_bytes() == (
                b"Lesson notes"
            )
        finally:
            await engine.dispose()

    run_async(scenario())


def test_authenticated_admin_can_preview_uploaded_text_file(tmp_path, monkeypatch):
    text_content = b"Admin text preview"
    stored_file = tmp_path / "user-1" / "stored.txt"
    stored_file.parent.mkdir(parents=True)
    stored_file.write_text("Stored upload preview", encoding="utf-8")
    image_content = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde"
    )
    monkeypatch.setenv("CLASSROOM_UPLOAD_ROOT", str(tmp_path))

    async def scenario():
        engine, async_session_maker = await make_session(tmp_path)

        try:
            async with async_session_maker() as db:
                await seed_admin_users(db)
                db.add(
                    UploadedFile(
                        id=1,
                        owner_id=1,
                        filename="sample.txt",
                        content_type="text/plain",
                        size=len(text_content),
                        storage_path="missing-sample.txt",
                        content=text_content,
                    )
                )
                db.add(
                    UploadedFile(
                        id=2,
                        owner_id=1,
                        filename="image.png",
                        content_type="image/png",
                        size=len(image_content),
                        storage_path="missing-image.png",
                        content=image_content,
                    )
                )
                db.add(
                    UploadedFile(
                        id=3,
                        owner_id=1,
                        filename="stored.txt",
                        content_type="text/plain",
                        size=stored_file.stat().st_size,
                        storage_path="user-1/stored.txt",
                    )
                )
                await db.commit()

            client = TestClient(
                make_admin_app(
                    engine,
                    views=[UserAdmin(User), UploadedFileAdmin(UploadedFile)],
                    include_file_preview_route=True,
                ),
                follow_redirects=False,
            )
            login_response = client.post(
                "/admin/login",
                data={
                    "username": "admin@example.com",
                    "password": "Admin_12345",
                },
            )
            assert login_response.status_code == 303

            detail_response = client.get("/admin/uploaded-file/detail/1")
            assert detail_response.status_code == 200
            assert "/admin/uploaded-files/1/preview" in detail_response.text

            preview_response = client.get("/admin/uploaded-files/1/preview")
            assert preview_response.status_code == 200
            assert preview_response.text == "Admin text preview"
            assert preview_response.headers["content-type"].startswith("text/plain")

            image_detail_response = client.get("/admin/uploaded-file/detail/2")
            assert image_detail_response.status_code == 200
            assert "/admin/uploaded-files/2/preview" in image_detail_response.text
            assert "<img" in image_detail_response.text

            image_preview_response = client.get("/admin/uploaded-files/2/preview")
            assert image_preview_response.status_code == 200
            assert image_preview_response.content == image_content
            assert image_preview_response.headers["content-type"].startswith("image/png")

            stored_preview_response = client.get("/admin/uploaded-files/3/preview")
            assert stored_preview_response.status_code == 200
            assert stored_preview_response.text == "Stored upload preview"
        finally:
            await engine.dispose()

    run_async(scenario())
