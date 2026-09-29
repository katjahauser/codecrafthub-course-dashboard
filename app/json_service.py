import json
from pathlib import Path


DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "api"
    / "courses"
    / "courses.json"
)


def read_courses():
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_courses(courses):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(courses, file, indent=2)


def find_course(course_id):
    courses = read_courses()

    return next(
        (course for course in courses if course["id"] == course_id),
        None
    )


def create_course(course):
    courses = read_courses()
    courses.append(course)
    write_courses(courses)

    return course


def update_course(course_id, updated_course):
    courses = read_courses()

    for index, course in enumerate(courses):
        if course["id"] == course_id:
            courses[index] = updated_course
            write_courses(courses)
            return updated_course

    return None


def delete_course(course_id):
    courses = read_courses()

    filtered_courses = [
        course for course in courses
        if course["id"] != course_id
    ]

    if len(filtered_courses) == len(courses):
        return False

    write_courses(filtered_courses)
    return True