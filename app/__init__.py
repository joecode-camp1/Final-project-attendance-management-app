from flask import Flask
from app.config import Config
from app.database.extensions import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # ✅ Import models before db.create_all() so SQLAlchemy registers all tables
    from app.models.user_model import User
    from app.models.attendance_model import AttendanceSession, AttendanceRecord
    from app.models.student_model import Class

    from app.controllers.home_controller import home_bp
    from app.controllers.auth_controller import auth_bp
    from app.controllers.dashboard_controller import dashboard_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    with app.app_context():
        db.create_all()  # now sees all 3 models: users, attendance_sessions, attendance_records, classes

    return app