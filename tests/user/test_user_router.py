from datetime import datetime
from unittest.mock import AsyncMock

import pytest


def user_response_payload(user_id: int = 1):
    return {
        "id": user_id,
        "email": "teacher@example.com",
        "first_name": "Test",
        "second_name": "Teacher",
        "third_name": "User",
        "is_active": True,
        "is_superuser": False,
        "is_verified": True,
        "is_teacher": True,
    }


def lms_summary_payload():
    submitted_at = datetime(2026, 5, 1).isoformat()
    return {
        "user": user_response_payload(),
        "courses": [
            {
                "course_id": 10,
                "title": "Python LMS",
                "role": "student",
                "status": "active",
                "is_active": True,
            }
        ],
        "submissions": [
            {
                "submission_id": 3,
                "assignment_id": 7,
                "assignment_title": "Profile CRUD",
                "course_id": 10,
                "course_title": "Python LMS",
                "status": "graded",
                "submitted_at": submitted_at,
                "graded_at": submitted_at,
                "grade_score": 9,
                "grade_feedback": "Solid",
            }
        ],
    }


def test_read_me_returns_current_user(client):
    response = client.get("/users/me/")

    assert response.status_code == 200
    assert response.json() == user_response_payload()


def test_update_me_updates_profile(client, db_session, monkeypatch):
    payload = {"first_name": "Updated"}
    expected_user = user_response_payload()
    expected_user["first_name"] = "Updated"
    update_mock = AsyncMock(return_value=expected_user)
    monkeypatch.setattr("user.router.update_current_user_profile", update_mock)

    response = client.patch("/users/me/", json=payload)

    assert response.status_code == 200
    assert response.json() == expected_user

    call_kwargs = update_mock.await_args.kwargs
    assert call_kwargs["db"] is db_session
    assert call_kwargs["user"].id == 1
    assert call_kwargs["user_data"].model_dump(exclude_unset=True) == payload


def test_read_users_scopes_query_to_current_teacher(client, db_session, monkeypatch):
    expected_users = [user_response_payload()]
    get_users_mock = AsyncMock(return_value=expected_users)
    monkeypatch.setattr("user.router.get_users", get_users_mock)

    response = client.get("/users/?search=teach&limit=10&offset=0")

    assert response.status_code == 200
    assert response.json() == expected_users

    call_kwargs = get_users_mock.await_args.kwargs
    assert call_kwargs["db"] is db_session
    assert call_kwargs["actor"].id == 1
    assert call_kwargs["search"] == "teach"
    assert call_kwargs["limit"] == 10
    assert call_kwargs["offset"] == 0


def test_read_course_user_progress_uses_lms_access_context(
    client,
    db_session,
    monkeypatch,
):
    expected_summary = lms_summary_payload()
    progress_mock = AsyncMock(return_value=expected_summary)
    monkeypatch.setattr("user.router.get_course_user_progress", progress_mock)

    response = client.get("/users/2/courses/10/progress/")

    assert response.status_code == 200
    assert response.json() == expected_summary

    call_kwargs = progress_mock.await_args.kwargs
    assert call_kwargs["db"] is db_session
    assert call_kwargs["course_id"] == 10
    assert call_kwargs["user_id"] == 2
    assert call_kwargs["actor"].id == 1


@pytest.mark.parametrize(
    ("method", "url", "payload"),
    [
        ("patch", "/users/me/", {"first_name": ""}),
        ("get", "/users/?limit=0", None),
        ("get", "/users/?offset=-1", None),
        ("get", "/users/?search=", None),
    ],
)
def test_user_router_rejects_invalid_input(client, method, url, payload):
    if payload is None:
        response = getattr(client, method)(url)
    else:
        response = getattr(client, method)(url, json=payload)

    assert response.status_code == 422
