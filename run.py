from flask import Flask, send_from_directory

from app.course_routes import courses_bp


def create_app():
    app = Flask(__name__)
    app.json.sort_keys = False

    app.register_blueprint(courses_bp, url_prefix="/api/courses")

    @app.get("/")
    def index():
        return send_from_directory(app.root_path, "index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)