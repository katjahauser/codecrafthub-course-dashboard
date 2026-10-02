from datetime import datetime
import re

import pytest

from app import json_service
from run import create_app


COURSE_FIELDS = (
    "id",
    "title",
    "description",
    "target_date",
    "status",
    "created_at",
)


def valid_course(**overrides):
    course = {
        "title": "New Course-101/Python (Basics)",
        "description": "Learn Python, Flask! Build/API?",
        "target_date": "2026-12-20",
        "status": "Not started",
    }
    course.update(overrides)
    return course


def existing_course(**overrides):
    course = {
        "id": 1,
        "title": "Existing Course",
        "description": "An existing description.",
        "target_date": "2026-11-30",
        "status": "In progress",
        "created_at": "2026-10-02 09:00:00",
    }
    course.update(overrides)
    return course


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(json_service, "DATA_FILE", tmp_path / "courses.json")
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
    assert courses[0]["id"] == 1
    assert courses[0]["title"] == "New Course-101/Python (Basics)"
    assert tuple(courses[0]) == COURSE_FIELDS
    datetime.strptime(courses[0]["created_at"], "%Y-%m-%d %H:%M:%S")


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
        description="An existing description.",
    )

    response = client.post("/api/courses", json=duplicate_title)

    assert response.status_code == 409
    assert len(json_service.read_courses()) == 1


ILLEGAL_COURSE_CASES = [
    pytest.param({"target_date": "2026-02-30"}, id="invalid date"),
    pytest.param({"target_date": "20260228"}, id="date not hyphenated"),
    pytest.param({"status": "Paused"}, id="invalid status"),
    pytest.param({"title": "New@Course"}, id="title special character"),
    pytest.param({"title": "A" * 257}, id="title too long"),
    pytest.param(
        {"description": "A description with @ character."},
        id="description special character",
    ),
    pytest.param({"description": "A" * 1025}, id="description too long"),
]


@pytest.mark.parametrize("overrides", ILLEGAL_COURSE_CASES)
def test_add_course_with_illegal_data_fails(client, overrides):
    response = client.post("/api/courses", json=valid_course(**overrides))

    assert response.status_code == 400


def test_edit_course_with_legal_data_succeeds(client):
    seed_course()
    original_created_at = json_service.read_courses()[0]["created_at"]
    update = valid_course(title="Updated Course")

    response = client.put("/api/courses/1", json=update)

    assert response.status_code == 200
    assert response.get_json() == (
        'Successfully updated "title" to "Updated Course", '
        '"description" to "Learn Python, Flask! Build/API?", '
        '"target_date" to "2026-12-20" and "status" to "Not started".'
    )
    assert json_service.read_courses()[0]["title"] == "Updated Course"
    assert json_service.read_courses()[0]["status"] == "Not started"
    assert json_service.read_courses()[0]["created_at"] == original_created_at


def test_put_with_missing_editable_fields_updates_only_supplied_fields(client):
    original_course = seed_course()

    response = client.put("/api/courses/1", json={"title": "Updated Course"})

    assert response.status_code == 200
    assert response.get_json() == 'Successfully updated "title" to "Updated Course".'
    updated_course = json_service.read_courses()[0]
    assert updated_course["title"] == "Updated Course"
    assert updated_course["description"] == original_course["description"]
    assert updated_course["target_date"] == original_course["target_date"]
    assert updated_course["status"] == original_course["status"]


@pytest.mark.parametrize("overrides", ILLEGAL_COURSE_CASES)
def test_edit_course_with_illegal_data_fails(client, overrides):
    seed_course()
    update = valid_course(title="Updated Course")
    update.update(overrides)
    response = client.put("/api/courses/1", json=update)

    assert response.status_code == 400


def test_delete_course_with_valid_id_succeeds(client):
    seed_course()

    response = client.delete("/api/courses/1")

    assert response.status_code == 200
    assert json_service.read_courses() == []


def test_delete_course_with_invalid_id_fails(client):
    response = client.delete("/api/courses/999")

    assert response.status_code == 404


def test_get_all_courses_succeeds(client):
    expected = seed_course()

    response = client.get("/api/courses")

    assert response.status_code == 200
    assert response.get_json() == [expected]


def test_get_course_stats_returns_total_count(client):
    json_service.write_courses([
        existing_course(id=1, status="Not started"),
        existing_course(id=2, title="Second Course", status="In progress"),
        existing_course(id=3, title="Third Course", status="Completed"),
    ])

    response = client.get("/api/courses/stats")

    assert response.status_code == 200
    assert response.get_json() == (
        "The total number of courses is 3. Course counts by status: "
        "Not started: 1, In progress: 1, Completed: 1."
    )


def test_get_course_stats_returns_zero_for_empty_collection(client):
    response = client.get("/api/courses/stats")

    assert response.status_code == 200
    assert response.get_json() == (
        "The total number of courses is 0. Course counts by status: "
        "Not started: 0, In progress: 0, Completed: 0."
    )


def test_get_course_stats_errors_when_status_counts_do_not_cover_all_courses(client):
    json_service.write_courses([
        existing_course(id=1, status="Archived"),
    ])

    response = client.get("/api/courses/stats")

    assert response.status_code == 500
    assert response.get_json() == {
        "error": "Course status counts do not match the total course count"
    }


def test_get_courses_with_invalid_command_fails(client):
    response = client.get("/api/unknown-courses")

    assert response.status_code == 404


def test_get_course_with_valid_id_succeeds(client):
    expected = seed_course()

    response = client.get("/api/courses/1")

    assert response.status_code == 200
    assert response.get_json() == expected


def test_get_course_with_invalid_id_fails(client):
    response = client.get("/api/courses/999")

    assert response.status_code == 404


def test_partial_course_edit_succeeds(client):
    seed_course()

    response = client.patch(
        "/api/courses/1",
        json={"title": "Partially Updated Course"},
    )

    assert response.status_code == 200
    assert response.get_json() == (
        'Successfully updated "title" to "Partially Updated Course".'
    )
    assert json_service.read_courses()[0]["title"] == "Partially Updated Course"


def test_partial_course_edit_lists_all_updated_fields(client):
    seed_course()

    response = client.patch(
        "/api/courses/1",
        json={"title": "New Title", "status": "Completed"},
    )

    assert response.status_code == 200
    assert response.get_json() == (
        'Successfully updated "title" to "New Title" and '
        '"status" to "Completed".'
    )


@pytest.mark.parametrize("method, path", [
    ("post", "/api/courses"),
    ("put", "/api/courses/1"),
    ("patch", "/api/courses/1"),
])
@pytest.mark.parametrize("field, value", [
    ("id", 99),
    ("created_at", "2026-01-01 00:00:00"),
])
def test_server_managed_fields_cannot_be_set(client, method, path, field, value):
    if method != "post":
        seed_course()
    course_data = valid_course(**{field: value})

    response = getattr(client, method)(path, json=course_data)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": f'Field "{field}" cannot be set manually'
    }


@pytest.mark.parametrize("method", ["put", "patch"])
def test_update_requires_at_least_one_editable_field(client, method):
    seed_course()

    response = getattr(client, method)("/api/courses/1", json={})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "At least one editable field must be provided"
    }


def test_missing_courses_file_is_created(client):
    response = client.get("/api/courses/")

    assert response.status_code == 200
    assert response.get_json() == []
    assert json_service.DATA_FILE.exists()


def test_read_file_error_returns_json_error(client, tmp_path, monkeypatch):
    courses_directory = tmp_path / "courses-directory"
    courses_directory.mkdir()
    monkeypatch.setattr(json_service, "DATA_FILE", courses_directory)

    response = client.get("/api/courses")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unable to read course data"}


def test_write_file_error_returns_json_error(client, tmp_path, monkeypatch):
    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("file", encoding="utf-8")
    monkeypatch.setattr(
        json_service,
        "DATA_FILE",
        blocked_parent / "courses.json",
    )

    response = client.post("/api/courses", json=valid_course())

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unable to write course data"}


def test_course_file_contents_follow_title_and_description_rules():
    title_pattern = re.compile(r"[A-Za-z0-9 /()-]+")
    description_pattern = re.compile(r"[A-Za-z0-9 .,!?'\"/()-]+")

    for course in json_service.read_courses():
        assert title_pattern.fullmatch(course["title"])
        assert description_pattern.fullmatch(course["description"])


def test_delete_keeps_course_ids_consecutive(client):
    courses = [
        existing_course(id=1),
        existing_course(id=2, title="Second Course"),
        existing_course(id=3, title="Third Course"),
    ]
    json_service.write_courses(courses)

    response = client.delete("/api/courses/2")

    assert response.status_code == 200
    assert [course["id"] for course in json_service.read_courses()] == [1, 2]

    create_response = client.post("/api/courses/", json=valid_course())

    assert create_response.status_code == 201
    assert [course["id"] for course in json_service.read_courses()] == [1, 2, 3]


def test_current_courses_file_has_three_courses():
    courses = json_service.read_courses()

    assert [course["id"] for course in courses] == [1, 2, 3]
    assert all("target_date" in course for course in courses)
    assert all("created_at" in course for course in courses)
