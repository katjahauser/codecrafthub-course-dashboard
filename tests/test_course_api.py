import pytest

from app import json_service
from run import create_app


COURSE_FIELDS = (
    "id",
    "title",
    "description",
    "targetEndDate",
    "status",
)


def valid_course(**overrides):
    course = {
        "title": "New Course-101 (Basics)",
        "description": "Learn Python, Flask! Build/API?",
        "targetEndDate": "2026-12-20",
        "status": "Not started",
    }
    course.update(overrides)
    return course


def existing_course(**overrides):
    course = {
        "id": "course-001",
        "title": "Existing Course",
        "description": "An existing description.",
        "targetEndDate": "2026-11-30",
        "status": "In progress",
    }
    course.update(overrides)
    return course


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(json_service, "DATA_FILE", tmp_path / "courses.json")
    json_service.write_courses([])
    return create_app().test_client()


def seed_course():
    course = existing_course()
    json_service.write_courses([course])
    return course


def test_add_course_with_all_fields_succeeds(client):
    response = client.post("/api/courses", json=valid_course())

    assert response.status_code == 201
    courses = json_service.read_courses()
    assert len(courses) == 1
    assert courses[0]["id"] == "course-001"
    assert courses[0]["title"] == "New Course-101 (Basics)"
    assert tuple(courses[0]) == COURSE_FIELDS


def test_add_course_missing_one_field_fails(client):
    course = valid_course()
    del course["status"]

    response = client.post("/api/courses", json=course)

    assert response.status_code == 400


def test_add_course_missing_multiple_fields_fails(client):
    response = client.post(
        "/api/courses",
        json={"title": "New Course"},
    )

    assert response.status_code == 400


def test_add_course_with_existing_title_fails(client):
    seed_course()
    duplicate_title = valid_course(
        title="Existing Course",
        description="A different description.",
    )

    response = client.post("/api/courses", json=duplicate_title)

    assert response.status_code == 409
    assert len(json_service.read_courses()) == 1


ILLEGAL_COURSE_CASES = [
    pytest.param({"targetEndDate": "2026-02-30"}, id="invalid date"),
    pytest.param({"status": "Paused"}, id="invalid status"),
    pytest.param({"title": "A" * 257}, id="title too long"),
    pytest.param({"title": "New@Course"}, id="title has disallowed character"),
    pytest.param({"description": "A" * 1025}, id="description too long"),
    pytest.param(
        {"description": "A description with @ sign."},
        id="description has disallowed character",
    ),
]


@pytest.mark.parametrize("overrides", ILLEGAL_COURSE_CASES)
def test_add_course_with_illegal_data_fails(client, overrides):
    response = client.post("/api/courses", json=valid_course(**overrides))

    assert response.status_code == 400


def test_edit_course_with_legal_data_succeeds(client):
    seed_course()
    update = valid_course(title="Updated Course")

    response = client.put("/api/courses/course-001", json=update)

    assert response.status_code == 200
    assert json_service.read_courses()[0]["title"] == "Updated Course"


@pytest.mark.parametrize("overrides", ILLEGAL_COURSE_CASES)
def test_edit_course_with_illegal_data_fails(client, overrides):
    seed_course()
    update = valid_course(title="Updated Course")
    update.update(overrides)
    response = client.put("/api/courses/course-001", json=update)

    assert response.status_code == 400


def test_delete_course_with_valid_id_succeeds(client):
    seed_course()

    response = client.delete("/api/courses/course-001")

    assert response.status_code == 200
    assert json_service.read_courses() == []


def test_delete_course_with_invalid_id_fails(client):
    response = client.delete("/api/courses/course-999")

    assert response.status_code == 404


def test_get_all_courses_succeeds(client):
    expected = seed_course()

    response = client.get("/api/courses")

    assert response.status_code == 200
    assert response.get_json() == [expected]


def test_get_courses_with_invalid_command_fails(client):
    response = client.get("/api/unknown-courses")

    assert response.status_code == 404


def test_get_course_with_valid_id_succeeds(client):
    expected = seed_course()

    response = client.get("/api/courses/course-001")

    assert response.status_code == 200
    assert response.get_json() == expected


def test_get_course_with_invalid_id_fails(client):
    response = client.get("/api/courses/course-999")

    assert response.status_code == 404


def test_partial_course_edit_fails(client):
    seed_course()

    response = client.patch(
        "/api/courses/course-001",
        json={"title": "Partially Updated Course"},
    )

    assert response.status_code == 400
