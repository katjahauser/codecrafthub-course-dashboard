from datetime import date

from flask import Blueprint, jsonify, request

from .json_service import (
    create_course,
    delete_course,
    find_course,
    read_courses,
    update_course,
)


courses_bp = Blueprint("courses", __name__)

ALLOWED_STATUSES = {
    "Not started",
    "In progress",
    "Completed",
}

REQUIRED_FIELDS = {
    "title",
    "description",
    "targetEndDate",
    "status",
}


def validate_course_data(data, partial=False):
    if not isinstance(data, dict):
        return "Request body must be a JSON object"

    if not partial:
        missing_fields = REQUIRED_FIELDS - data.keys()

        if missing_fields:
            return (
                "Missing required fields: "
                + ", ".join(sorted(missing_fields))
            )

    if "title" in data:
        if not isinstance(data["title"], str) or not data["title"].strip():
            return "title must be a non-empty string"

    if "description" in data:
        if (
            not isinstance(data["description"], str)
            or not data["description"].strip()
        ):
            return "description must be a non-empty string"

    if "targetEndDate" in data:
        try:
            date.fromisoformat(data["targetEndDate"])
        except (TypeError, ValueError):
            return "targetEndDate must use YYYY-MM-DD format"

    if "status" in data:
        if data["status"] not in ALLOWED_STATUSES:
            return (
                "status must be one of: "
                + ", ".join(sorted(ALLOWED_STATUSES))
            )

    return None


@courses_bp.get("")
def get_courses():
    return jsonify(read_courses()), 200


@courses_bp.get("/<course_id>")
def get_course(course_id):
    course = find_course(course_id)

    if course is None:
        return jsonify({"error": "Course not found"}), 404

    return jsonify(course), 200


@courses_bp.post("")
def add_course():
    data = request.get_json(silent=True)
    validation_error = validate_course_data(data)

    if validation_error:
        return jsonify({"error": validation_error}), 400

    course = {
        "title": data["title"].strip(),
        "description": data["description"].strip(),
        "targetEndDate": data["targetEndDate"],
        "status": data["status"],
    }

    course = create_course(course)
    if course is None:
        return jsonify({"error": "A course with the same title and/or description already exists."}), 409

    return jsonify(course), 201


@courses_bp.put("/<course_id>")
def replace_course(course_id):
    existing_course = find_course(course_id)

    if existing_course is None:
        return jsonify({"error": "Course not found"}), 404

    data = request.get_json(silent=True)
    validation_error = validate_course_data(data)

    if validation_error:
        return jsonify({"error": validation_error}), 400

    updated_course = {
        "id": course_id,
        "title": data["title"].strip(),
        "description": data["description"].strip(),
        "targetEndDate": data["targetEndDate"],
        "status": data["status"],
    }

    updated_course = update_course(course_id, updated_course)

    return jsonify(updated_course), 200


@courses_bp.patch("/<course_id>")
def partially_update_course(course_id):
    existing_course = find_course(course_id)

    if existing_course is None:
        return jsonify({"error": "Course not found"}), 404

    data = request.get_json(silent=True)
    validation_error = validate_course_data(data, partial=True)

    if validation_error:
        return jsonify({"error": validation_error}), 400

    updated_course = existing_course.copy()

    for field in REQUIRED_FIELDS:
        if field in data:
            value = data[field]
            updated_course[field] = (
                value.strip()
                if field in {"title", "description"}
                else value
            )

    update_course(course_id, updated_course)

    return jsonify(updated_course), 200


@courses_bp.delete("/<course_id>")
def remove_course(course_id):
    deleted = delete_course(course_id)
    if not deleted:
        return jsonify({"error": "Course not found"}), 404

    return jsonify(deleted), 200