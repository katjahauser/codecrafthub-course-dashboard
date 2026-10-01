import tempfile
import unittest
from pathlib import Path

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


class CourseApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_data_file = json_service.DATA_FILE
        json_service.DATA_FILE = Path(self.temporary_directory.name) / "courses.json"
        json_service.write_courses([])

        self.client = create_app().test_client()

    def tearDown(self):
        json_service.DATA_FILE = self.original_data_file
        self.temporary_directory.cleanup()

    def seed_course(self):
        course = existing_course()
        json_service.write_courses([course])
        return course

    def test_add_course_with_all_fields_succeeds(self):
        response = self.client.post("/api/courses", json=valid_course())

        self.assertEqual(response.status_code, 201)
        courses = json_service.read_courses()
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0]["id"], "course-001")
        self.assertEqual(courses[0]["title"], "New Course-101 (Basics)")
        self.assertEqual(tuple(courses[0]), COURSE_FIELDS)

    def test_add_course_missing_one_field_fails(self):
        course = valid_course()
        del course["status"]

        response = self.client.post("/api/courses", json=course)

        self.assertEqual(response.status_code, 400)

    def test_add_course_missing_multiple_fields_fails(self):
        response = self.client.post(
            "/api/courses",
            json={"title": "New Course"},
        )

        self.assertEqual(response.status_code, 400)

    def test_add_course_with_existing_title_fails(self):
        self.seed_course()
        duplicate_title = valid_course(
            title="Existing Course",
            description="A different description.",
        )

        response = self.client.post("/api/courses", json=duplicate_title)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(json_service.read_courses()), 1)

    def test_add_course_with_illegal_data_fails(self):
        illegal_cases = {
            "invalid date": {"targetEndDate": "2026-02-30"},
            "invalid status": {"status": "Paused"},
            "title too long": {"title": "A" * 257},
            "title has disallowed character": {"title": "New@Course"},
            "description too long": {"description": "A" * 1025},
            "description has disallowed character": {
                "description": "A description with @ sign."
            },
        }

        for case_name, overrides in illegal_cases.items():
            with self.subTest(case=case_name):
                json_service.write_courses([])
                response = self.client.post(
                    "/api/courses",
                    json=valid_course(**overrides),
                )
                self.assertEqual(response.status_code, 400)

    def test_edit_course_with_legal_data_succeeds(self):
        self.seed_course()
        update = valid_course(title="Updated Course")

        response = self.client.put("/api/courses/course-001", json=update)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json_service.read_courses()[0]["title"], "Updated Course")

    def test_edit_course_with_illegal_data_fails(self):
        illegal_cases = {
            "invalid date": {"targetEndDate": "2026-02-30"},
            "invalid status": {"status": "Paused"},
            "title too long": {"title": "A" * 257},
            "title has disallowed character": {"title": "Updated@Course"},
            "description too long": {"description": "A" * 1025},
            "description has disallowed character": {
                "description": "A description with @ sign."
            },
        }

        for case_name, overrides in illegal_cases.items():
            with self.subTest(case=case_name):
                self.seed_course()
                update = valid_course(title="Updated Course")
                update.update(overrides)
                response = self.client.put(
                    "/api/courses/course-001",
                    json=update,
                )
                self.assertEqual(response.status_code, 400)

    def test_delete_course_with_valid_id_succeeds(self):
        self.seed_course()

        response = self.client.delete("/api/courses/course-001")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json_service.read_courses(), [])

    def test_delete_course_with_invalid_id_fails(self):
        response = self.client.delete("/api/courses/course-999")

        self.assertEqual(response.status_code, 404)

    def test_get_all_courses_succeeds(self):
        expected = self.seed_course()

        response = self.client.get("/api/courses")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [expected])

    def test_get_courses_with_invalid_command_fails(self):
        response = self.client.get("/api/unknown-courses")

        self.assertEqual(response.status_code, 404)

    def test_get_course_with_valid_id_succeeds(self):
        expected = self.seed_course()

        response = self.client.get("/api/courses/course-001")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), expected)

    def test_get_course_with_invalid_id_fails(self):
        response = self.client.get("/api/courses/course-999")

        self.assertEqual(response.status_code, 404)

    def test_partial_course_edit_fails(self):
        self.seed_course()

        response = self.client.patch(
            "/api/courses/course-001",
            json={"title": "Partially Updated Course"},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
