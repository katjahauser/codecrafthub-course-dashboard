from flask import Flask

from app.course_routes import courses_bp


def create_app():
    app = Flask(__name__)

    app.register_blueprint(courses_bp, url_prefix="/api/courses")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)