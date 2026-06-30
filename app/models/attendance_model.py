from datetime import datetime, timezone
from app.database.extensions import db


class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'

    id = db.Column(db.Integer, primary_key=True)

    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)

    location = db.Column(db.String(200), nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    # ---- Relationships ----
    # `class_` (trailing underscore) avoids clashing with the `class` keyword.
    # Assumes your existing Class model exposes a `name` column and does NOT
    # already declare a back_populates/backref of the same name — if it does,
    # drop `backref=` here and wire it from the Class side instead.
    class_ = db.relationship('Class', backref='attendance_sessions', foreign_keys=[class_id])
    teacher = db.relationship('User', backref='attendance_sessions_taught', foreign_keys=[teacher_id])
    records = db.relationship('AttendanceRecord', back_populates='session', lazy='select')


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)

    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    student_name = db.Column(db.String(100), nullable=False)

    status = db.Column(db.String(20), nullable=False)

    sign_in_time = db.Column(db.DateTime)
    sign_out_time = db.Column(db.DateTime)

    total_time_minutes = db.Column(db.Integer)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    # ---- Relationships ----
    session = db.relationship('AttendanceSession', back_populates='records')
    student = db.relationship('User', backref='attendance_records', foreign_keys=[student_id])