import json
from datetime import datetime
from pathlib import Path


DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "api"
    / "courses"
    / "courses.json"
)
COURSE_FIELDS = (
    "id",
    "title",
    "description",
    "target_date",
    "status",
    "created_at",
)


class CourseStorageError(Exception):
    pass


def order_course(course):
    ordered_course = {
        field: course[field]
        for field in COURSE_FIELDS
        if field in course
    }
    ordered_course.update(
        (field, value)
        for field, value in course.items()
        if field not in ordered_course
    )

    return ordered_course


def read_courses():
    if not DATA_FILE.exists():
        write_courses([])
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            courses = json.load(file)
        if not isinstance(courses, list) or not all(
            isinstance(course, dict) for course in courses
        ):
            raise ValueError("Course data must be a JSON array of objects")
        return [order_course(course) for course in courses]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise CourseStorageError("Unable to read course data") from error


def write_courses(courses):
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump([order_course(course) for course in courses], file, indent=2)
    except (OSError, TypeError, ValueError) as error:
        raise CourseStorageError("Unable to write course data") from error


def _renumber_courses(courses):
    for course_id, course in enumerate(courses, start=1):
        course["id"] = course_id


def find_course(course_id):
    courses = read_courses()

    return next(
        (course for course in courses if course["id"] == course_id),
        None
    )


def create_course(course):
    courses = read_courses()
    
    if any(
        existing_course.get("title", "").strip() == course["title"].strip()
        and existing_course.get("description", "").strip()
        == course["description"].strip()
        for existing_course in courses
    ):
        return None
        

    course["id"] = len(courses) + 1
    course["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for field, value in course.items():
        course[field] = value.strip() if isinstance(value, str) else value

    courses.append(course)
    write_courses(courses)

    return f"Successfully created course '{course['title']}' with ID '{course['id']}'."


def update_course(course_id, updated_course):
    courses = read_courses()

    for index, course in enumerate(courses):
        if course["id"] == course_id:
            courses[index] = updated_course
            write_courses(courses)
            return f"The course '{course['title']}' with ID '{course_id}' has been updated successfully."

    return None


def delete_course(course_id):
    courses = read_courses()
    removed_course = next(
        (course for course in courses if course["id"] == course_id),
        None,
    )
    if removed_course is None:
        return False

    filtered_courses = [course for course in courses if course is not removed_course]
    _renumber_courses(filtered_courses)
    write_courses(filtered_courses)
    return f"The course '{removed_course['title']}' with ID '{course_id}' has been deleted successfully."