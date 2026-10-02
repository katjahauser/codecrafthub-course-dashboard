import re
from datetime import date
from enum import Enum
import json

from flask import Blueprint, jsonify, request

from .json_service import (
    CourseStorageError,
    create_course,
    delete_course,
    find_course,
    read_courses,
    update_course,
)


courses_bp = Blueprint("courses", __name__)


class CourseStatus(str, Enum):
    NOT_STARTED = "Not started"
    IN_PROGRESS = "In progress"
    COMPLETED = "Completed"


ALLOWED_STATUSES = {status.value for status in CourseStatus}
TITLE_PATTERN = re.compile(r"[A-Za-z0-9 /()-]+")
DESCRIPTION_PATTERN = re.compile(r"[A-Za-z0-9 .,!?'\"/()-]+")
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
MAX_TITLE_LENGTH = 256
MAX_DESCRIPTION_LENGTH = 1024

REQUIRED_FIELDS = {
    "title",
    "description",
    "target_date",
    "status",
}
EDITABLE_FIELDS = ("title", "description", "target_date", "status")
SERVER_MANAGED_FIELDS = {"id", "created_at"}


def validate_course_data(data, partial=False):
    if not isinstance(data, dict):
        return "Request body must be a JSON object"

    for field in SERVER_MANAGED_FIELDS:
        if field in data:
            return f'Field "{field}" cannot be set manually'

    unknown_fields = data.keys() - REQUIRED_FIELDS
    if unknown_fields:
        return "Unsupported fields: " + ", ".join(sorted(unknown_fields))

    if not partial:
        missing_fields = REQUIRED_FIELDS - data.keys()

        if missing_fields:
            return (
                "Missing required fields: "
                + ", ".join(sorted(missing_fields))
            )

    if "title" in data:
        title = data["title"]
        if not isinstance(title, str) or not title.strip():
            return "title must be a non-empty string"
        if len(title) > MAX_TITLE_LENGTH or not TITLE_PATTERN.fullmatch(title):
            return (
                "title may contain only letters, numbers, spaces, and hyphens "
                f"and must be at most {MAX_TITLE_LENGTH} characters"
            )

    if "description" in data:
        description = data["description"]
        if not isinstance(description, str) or not description.strip():
            return "description must be a non-empty string"
        if (
            len(description) > MAX_DESCRIPTION_LENGTH
            or not DESCRIPTION_PATTERN.fullmatch(description)
        ):
            return (
                "description contains unsupported characters or exceeds "
                f"{MAX_DESCRIPTION_LENGTH} characters"
            )

    if "target_date" in data:
        target_date = data["target_date"]
        if (
            not isinstance(target_date, str)
            or not DATE_PATTERN.fullmatch(target_date)
        ):
            return "target_date must use YYYY-MM-DD format"
        try:
            date.fromisoformat(target_date)
        except (TypeError, ValueError):
            return "target_date must use YYYY-MM-DD format"

    if "status" in data:
        if not isinstance(data["status"], str) or data["status"] not in ALLOWED_STATUSES:
            return (
                "status must be one of: "
                + ", ".join(sorted(ALLOWED_STATUSES))
            )

    return None


@courses_bp.app_errorhandler(CourseStorageError)
def handle_course_storage_error(error):
    return jsonify({"error": str(error)}), 500


@courses_bp.get("")
@courses_bp.get("/")
def get_courses():
    return jsonify(read_courses()), 200


@courses_bp.get("/stats")
def get_course_stats():
    return jsonify(f"The total number of courses is {len(read_courses())}."), 200


@courses_bp.get("/<int:course_id>")
def get_course(course_id):
    course = find_course(course_id)

    if course is None:
        return jsonify({"error": "Course not found"}), 404

    return jsonify(course), 200


@courses_bp.post("")
@courses_bp.post("/")
def add_course():
    data = request.get_json(silent=True)
    validation_error = validate_course_data(data)

    if validation_error:
        return jsonify({"error": validation_error}), 400

    course = {
        "title": data["title"].strip(),
        "description": data["description"].strip(),
        "target_date": data["target_date"],
        "status": data["status"],
    }

    course = create_course(course)
    if course is None:
        return jsonify({"error": "A course with the same title and/or description already exists."}), 409

    return jsonify(course), 201


def update_course_fields(course_id):
    existing_course = find_course(course_id)

    if existing_course is None:
        return jsonify({"error": "Course not found"}), 404

    data = request.get_json(silent=True)
    validation_error = validate_course_data(data, partial=True)

    if validation_error:
        return jsonify({"error": validation_error}), 400

    updated_fields = [field for field in EDITABLE_FIELDS if field in data]
    if not updated_fields:
        return jsonify({"error": "At least one editable field must be provided"}), 400

    updated_course = existing_course.copy()
    for field in updated_fields:
        value = data[field]
        updated_course[field] = (
            value.strip()
            if field in {"title", "description"}
            else value
        )

    update_course(course_id, updated_course)
    changes = [
        f'"{field}" to {json.dumps(updated_course[field], ensure_ascii=False)}'
        for field in updated_fields
    ]
    if len(changes) == 1:
        message_changes = changes[0]
    else:
        message_changes = ", ".join(changes[:-1]) + " and " + changes[-1]

    return jsonify(f"Successfully updated {message_changes}."), 200


@courses_bp.put("/<int:course_id>")
def replace_course(course_id):
    return update_course_fields(course_id)


@courses_bp.patch("/<int:course_id>")
def partially_update_course(course_id):
    return update_course_fields(course_id)


@courses_bp.delete("/<int:course_id>")
def remove_course(course_id):
    deleted = delete_course(course_id)
    if not deleted:
        return jsonify({"error": "Course not found"}), 404

    return jsonify(deleted), 200