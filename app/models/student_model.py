from datetime import datetime, timezone
from app.database.extensions import db


class Class(db.Model):
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    code = db.Column(db.String(20), unique=True, nullable=False)

    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id', use_alter=True, name='fk_class_teacher_id'))

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    # ================= RELATIONSHIPS =================

    teacher = db.relationship(
        'User',
        backref='classes_taught',
        foreign_keys=[teacher_id]
    )

    students = db.relationship(
        'User',
        backref='class_assigned',
        primaryjoin="Class.id==User.class_id",
        foreign_keys="[User.class_id]",
        lazy=True
    )