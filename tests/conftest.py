from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from database.engine import get_async_session
from main import app
from settings import current_user


@pytest.fixture
def test_user():
    return SimpleNamespace(
        id=1,
        email="teacher@example.com",
        first_name="Test",
        second_name="Teacher",
        third_name="User",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        is_teacher=True,
    )


@pytest.fixture
def db_session():
    return object()


@pytest.fixture
def client(test_user, db_session):
    async def override_current_user():
        return test_user

    async def override_db_session():
        yield db_session

    app.dependency_overrides[current_user] = override_current_user
    app.dependency_overrides[get_async_session] = override_db_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
