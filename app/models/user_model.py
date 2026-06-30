from datetime import datetime, timezone
from app.database.extensions import db  # ✅ single import block


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    unique_id = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default='student'
    )  # student | teacher | admin

    is_approved = db.Column(db.Boolean, default=True)

    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )