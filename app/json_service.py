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


def _course_number(course_id):
    prefix = "course-"
    if not isinstance(course_id, str) or not course_id.startswith(prefix):
        return None

    number = course_id[len(prefix):]
    return int(number) if number.isdigit() else None


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
        

    course_numbers = []
    for existing_course in courses:
        number = _course_number(existing_course.get("id"))
        if number is not None:
            course_numbers.append(number)
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
    removed_course = next(
        (course for course in courses if course["id"] == course_id),
        None,
    )
    if removed_course is None:
        return False

    removed_number = _course_number(removed_course.get("id"))
    numbered_courses = [
        (number, course)
        for course in courses
        if (number := _course_number(course.get("id"))) is not None
    ]
    highest_number, highest_course = max(
        numbered_courses,
        key=lambda item: item[0],
        default=(None, None),
    )

    filtered_courses = [course for course in courses if course is not removed_course]
    if (
        removed_number is not None
        and highest_number is not None
        and removed_number < highest_number
    ):
        highest_course["id"] = removed_course["id"]
        filtered_courses.sort(
            key=lambda course: (
                _course_number(course.get("id")) is None,
                _course_number(course.get("id")) or 0,
            )
        )

    write_courses(filtered_courses)
    return f"The course with ID '{course_id}' has been deleted successfully."