from datetime import datetime
from unittest.mock import AsyncMock

import pytest


def course_response_payload(course_id: int = 1):
    timestamp = datetime(2026, 5, 1).isoformat()
    return {
        "id": course_id,
        "title": "Python Basics",
        "description": "Intro course",
        "is_active": True,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def lesson_response_payload(lesson_id: int = 1, course_id: int = 1):
    timestamp = datetime(2026, 5, 1).isoformat()
    return {
        "id": lesson_id,
        "course_id": course_id,
        "title": "SQLAlchemy models",
        "description": None,
        "position": 1,
        "starts_at": None,
        "ends_at": None,
        "is_published": True,
        "created_at": timestamp,
    }


def test_read_courses_returns_courses(client, db_session, monkeypatch):
    expected_courses = [course_response_payload()]
    get_all_courses_mock = AsyncMock(return_value=expected_courses)
    monkeypatch.setattr("classroom.router.get_all_courses", get_all_courses_mock)

    response = client.get("/classroom/courses/")

    assert response.status_code == 200
    assert response.json() == expected_courses
    get_all_courses_mock.assert_awaited_once()
    assert get_all_courses_mock.await_args.kwargs["db"] is db_session
    assert get_all_courses_mock.await_args.kwargs["user"].id == 1


def test_create_course_creates_course(client, db_session, monkeypatch):
    payload = {
        "title": "Python Advanced",
        "description": "Async backend",
        "is_active": True,
    }
    expected_course = course_response_payload()
    expected_course["title"] = payload["title"]
    expected_course["description"] = payload["description"]
    create_course_mock = AsyncMock(return_value=expected_course)
    monkeypatch.setattr("classroom.router.create_course", create_course_mock)

    response = client.post("/classroom/courses/", json=payload)

    assert response.status_code == 201
    assert response.json() == expected_course
    create_course_mock.assert_awaited_once()

    call_kwargs = create_course_mock.await_args.kwargs
    assert call_kwargs["db"] is db_session
    assert call_kwargs["course_data"].model_dump() == payload
    assert call_kwargs["user"].id == 1


def test_create_lesson_creates_lesson(client, db_session, monkeypatch):
    payload = {
        "title": "SQLAlchemy models",
        "description": None,
        "position": 1,
        "starts_at": None,
        "ends_at": None,
        "is_published": True,
    }
    expected_lesson = lesson_response_payload(course_id=10)
    create_lesson_mock = AsyncMock(return_value=expected_lesson)
    monkeypatch.setattr("classroom.router.create_lesson", create_lesson_mock)

    response = client.post("/classroom/courses/10/lessons/", json=payload)

    assert response.status_code == 201
    assert response.json() == expected_lesson
    create_lesson_mock.assert_awaited_once()

    call_kwargs = create_lesson_mock.await_args.kwargs
    assert call_kwargs["db"] is db_session
    assert call_kwargs["course_id"] == 10
    assert call_kwargs["lesson_data"].model_dump() == payload
    assert call_kwargs["user"].id == 1


def test_read_lesson_assignments_scopes_through_current_user(
    client,
    db_session,
    monkeypatch,
):
    expected_assignments = [
        {
            "id": 3,
            "lesson_id": 5,
            "title": "Design LMS models",
            "description": None,
            "deadline": None,
            "max_score": 100,
            "is_published": True,
            "created_at": datetime(2026, 5, 1).isoformat(),
        }
    ]
    get_lesson_assignments_mock = AsyncMock(return_value=expected_assignments)
    monkeypatch.setattr(
        "classroom.router.get_lesson_assignments",
        get_lesson_assignments_mock,
    )

    response = client.get("/classroom/lessons/5/assignments/")

    assert response.status_code == 200
    assert response.json() == expected_assignments

    call_kwargs = get_lesson_assignments_mock.await_args.kwargs
    assert call_kwargs["db"] is db_session
    assert call_kwargs["lesson_id"] == 5
    assert call_kwargs["user"].id == 1


def test_grade_submission_uses_current_user_as_grader(
    client,
    db_session,
    monkeypatch,
):
    payload = {"score": 11, "feedback": "Good work"}
    expected_grade = {
        "id": 7,
        "submission_id": 4,
        "grader_id": 1,
        "score": 11,
        "feedback": "Good work",
        "created_at": datetime(2026, 5, 1).isoformat(),
    }
    grade_submission_mock = AsyncMock(return_value=expected_grade)
    monkeypatch.setattr("classroom.router.grade_submission", grade_submission_mock)

    response = client.post("/classroom/submissions/4/grade/", json=payload)

    assert response.status_code == 200
    assert response.json() == expected_grade

    call_kwargs = grade_submission_mock.await_args.kwargs
    assert call_kwargs["db"] is db_session
    assert call_kwargs["submission_id"] == 4
    assert call_kwargs["grader_id"] == 1
    assert call_kwargs["grade_data"].model_dump() == payload


def test_upload_file_saves_file_and_creates_metadata(
    client,
    db_session,
    tmp_path,
    monkeypatch,
):
    create_uploaded_file_mock = AsyncMock(
        return_value={
            "id": 9,
            "owner_id": 1,
            "filename": "lesson.txt",
            "content_type": "text/plain",
            "size": 13,
            "storage_path": "user-1/generated_lesson.txt",
            "created_at": datetime(2026, 5, 1).isoformat(),
        }
    )
    monkeypatch.setenv("CLASSROOM_UPLOAD_ROOT", str(tmp_path))
    monkeypatch.setattr("classroom.router.create_uploaded_file", create_uploaded_file_mock)

    response = client.post(
        "/classroom/files/upload/",
        files={"file": ("lesson.txt", b"Hello upload!", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "lesson.txt"
    create_uploaded_file_mock.assert_awaited_once()

    call_kwargs = create_uploaded_file_mock.await_args.kwargs
    saved_path = tmp_path / call_kwargs["file_data"].storage_path
    assert call_kwargs["db"] is db_session
    assert call_kwargs["owner_id"] == 1
    assert call_kwargs["file_data"].filename == "lesson.txt"
    assert call_kwargs["file_data"].content_type == "text/plain"
    assert call_kwargs["file_data"].size == len(b"Hello upload!")
    assert call_kwargs["file_data"].content is None
    assert saved_path.read_bytes() == b"Hello upload!"


@pytest.mark.parametrize(
    ("method", "url", "payload"),
    [
        ("post", "/classroom/courses/", {"title": ""}),
        (
            "post",
            "/classroom/courses/1/lessons/",
            {"title": "Intro", "position": -1},
        ),
        (
            "post",
            "/classroom/lessons/1/assignments/",
            {"title": "Homework", "max_score": 0},
        ),
        ("post", "/classroom/submissions/1/grade/", {"score": -1}),
        (
            "post",
            "/classroom/files/",
            {"filename": "", "size": -1, "storage_path": ""},
        ),
    ],
)
def test_router_rejects_invalid_payloads(client, method, url, payload):
    response = getattr(client, method)(url, json=payload)

    assert response.status_code == 422
