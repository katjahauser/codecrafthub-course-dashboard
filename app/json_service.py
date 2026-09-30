import json
from pathlib import Path


DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "api"
    / "courses"
    / "courses.json"
)
COURSE_FIELDS = ("id", "title", "description", "targetEndDate", "status")


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
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        return [order_course(course) for course in json.load(file)]


def write_courses(courses):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump([order_course(course) for course in courses], file, indent=2)


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
        

    course_numbers = [
        int(existing_course["id"][len("course-"):])
        for existing_course in courses
        if isinstance(existing_course.get("id"), str)
        and existing_course["id"].startswith("course-")
        and existing_course["id"][len("course-"):].isdigit()
    ]
    course["id"] = f"course-{max(course_numbers, default=0) + 1:03d}"

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

    title_of_removed_course = next((course["title"] for course in courses if course["id"] == course_id), None)

    filtered_courses = [
        course for course in courses
        if course["id"] != course_id
    ]

    if len(filtered_courses) == len(courses):
        return False

    write_courses(filtered_courses)
    return f"The course with ID '{course_id}' has been deleted successfully."