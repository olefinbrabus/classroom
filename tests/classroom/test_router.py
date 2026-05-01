from unittest.mock import AsyncMock


def classroom_response_payload(classroom_id: int = 1):
    return {
        "id": classroom_id,
        "name": f"Room {classroom_id}",
        "description": f"Room {classroom_id} description",
    }


def user_response_payload(user_id: int = 1):
    return {
        "id": user_id,
        "email": f"user{user_id}@example.com",
        "first_name": "Test",
        "second_name": "User",
        "third_name": str(user_id),
        "is_active": True,
        "is_superuser": False,
        "is_verified": True,
        "is_teacher": False,
    }


def class_response_payload(class_id: int = 1):
    return {
        "id": class_id,
        "name": "Python Basics",
        "users": [user_response_payload(1), user_response_payload(2)],
        "classrooms": [classroom_response_payload(1), classroom_response_payload(2)],
    }


def test_read_classes_returns_classes(client, db_session, monkeypatch):
    expected_classes = [class_response_payload()]
    get_all_classes_mock = AsyncMock(return_value=expected_classes)
    monkeypatch.setattr("classroom.router.get_all_classes", get_all_classes_mock)

    response = client.get("/classroom/classes/")

    assert response.status_code == 200
    assert response.json() == expected_classes
    get_all_classes_mock.assert_awaited_once_with(db=db_session)


def test_create_class_creates_class(client, db_session, monkeypatch):
    payload = {
        "name": "Python Advanced",
        "users": [1, 2],
        "classrooms": [1, 2],
    }
    expected_class = class_response_payload()
    expected_class["name"] = payload["name"]
    create_class_mock = AsyncMock(return_value=expected_class)
    monkeypatch.setattr("classroom.router.create_class", create_class_mock)

    response = client.post("/classroom/classes/", json=payload)

    assert response.status_code == 200
    assert response.json() == expected_class
    create_class_mock.assert_awaited_once()

    call_kwargs = create_class_mock.await_args.kwargs
    assert call_kwargs["db"] is db_session
    assert call_kwargs["class_data"].model_dump() == payload


def test_read_class_returns_class(client, db_session, monkeypatch):
    expected_class = class_response_payload(class_id=10)
    get_class_mock = AsyncMock(return_value=expected_class)
    monkeypatch.setattr("classroom.router.get_class", get_class_mock)

    response = client.get("/classroom/classes/10/")

    assert response.status_code == 200
    assert response.json() == expected_class
    get_class_mock.assert_awaited_once_with(class_id=10, db=db_session)


def test_update_class_updates_name(client, db_session, monkeypatch):
    expected_class = class_response_payload(class_id=10)
    expected_class["name"] = "Updated Python"
    update_class_mock = AsyncMock(return_value=expected_class)
    monkeypatch.setattr("classroom.router.update_class", update_class_mock)

    response = client.patch("/classroom/classes/10/", json={"name": "Updated Python"})

    assert response.status_code == 200
    assert response.json() == expected_class
    update_class_mock.assert_awaited_once()

    call_kwargs = update_class_mock.await_args.kwargs
    assert call_kwargs["class_id"] == 10
    assert call_kwargs["db"] is db_session
    assert call_kwargs["class_data"].model_dump(exclude_unset=True) == {
        "name": "Updated Python",
    }


def test_delete_class_deletes_class(client, db_session, monkeypatch):
    delete_class_mock = AsyncMock(return_value={"id": 10, "deleted": True})
    monkeypatch.setattr("classroom.router.delete_class", delete_class_mock)

    response = client.delete("/classroom/classes/10/")

    assert response.status_code == 200
    assert response.json() == {"id": 10, "deleted": True}
    delete_class_mock.assert_awaited_once_with(class_id=10, db=db_session)


def test_add_user_to_class_creates_user_link(client, db_session, monkeypatch):
    expected_class = class_response_payload(class_id=10)
    add_user_to_class_mock = AsyncMock(return_value=expected_class)
    monkeypatch.setattr(
        "classroom.router.add_user_to_class",
        add_user_to_class_mock,
    )

    response = client.post("/classroom/classes/10/users/", json={"user_id": 2})

    assert response.status_code == 200
    assert response.json() == expected_class
    add_user_to_class_mock.assert_awaited_once_with(
        class_id=10,
        user_id=2,
        db=db_session,
    )


def test_remove_user_from_class_deletes_user_link(client, db_session, monkeypatch):
    expected_class = class_response_payload(class_id=10)
    expected_class["users"] = [user_response_payload(1)]
    remove_user_from_class_mock = AsyncMock(return_value=expected_class)
    monkeypatch.setattr(
        "classroom.router.remove_user_from_class",
        remove_user_from_class_mock,
    )

    response = client.delete("/classroom/classes/10/users/2/")

    assert response.status_code == 200
    assert response.json() == expected_class
    remove_user_from_class_mock.assert_awaited_once_with(
        class_id=10,
        user_id=2,
        db=db_session,
    )


def test_add_classroom_to_class_creates_classroom_link(
    client,
    db_session,
    monkeypatch,
):
    expected_class = class_response_payload(class_id=10)
    add_classroom_to_class_mock = AsyncMock(return_value=expected_class)
    monkeypatch.setattr(
        "classroom.router.add_classroom_to_class",
        add_classroom_to_class_mock,
    )

    response = client.post(
        "/classroom/classes/10/classrooms/",
        json={"classroom_id": 2},
    )

    assert response.status_code == 200
    assert response.json() == expected_class
    add_classroom_to_class_mock.assert_awaited_once_with(
        class_id=10,
        classroom_id=2,
        db=db_session,
    )


def test_remove_classroom_from_class_deletes_classroom_link(
    client,
    db_session,
    monkeypatch,
):
    expected_class = class_response_payload(class_id=10)
    expected_class["classrooms"] = [classroom_response_payload(1)]
    remove_classroom_from_class_mock = AsyncMock(return_value=expected_class)
    monkeypatch.setattr(
        "classroom.router.remove_classroom_from_class",
        remove_classroom_from_class_mock,
    )

    response = client.delete("/classroom/classes/10/classrooms/2/")

    assert response.status_code == 200
    assert response.json() == expected_class
    remove_classroom_from_class_mock.assert_awaited_once_with(
        class_id=10,
        classroom_id=2,
        db=db_session,
    )
