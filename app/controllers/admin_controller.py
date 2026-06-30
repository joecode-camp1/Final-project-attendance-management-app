# from flask import Blueprint, render_template, redirect, url_for, request, flash
# from app import db
# from app.models import User, Class  # assuming you have Class model

# admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# # =========================================================
# # DASHBOARD
# # =========================================================
# @admin_bp.route('/dashboard')
# def dashboard():
#     pending_users = User.query.filter_by(is_approved=False).all()
#     teachers = User.query.filter_by(role='teacher', is_approved=True).all()
#     students = User.query.filter_by(role='student', is_approved=True).all()

#     return render_template(
#         'admin/dashboard.html',
#         pending_users=pending_users,
#         teachers=teachers,
#         students=students
#     )


# # =========================================================
# # APPROVE USER
# # =========================================================
# @admin_bp.route('/approve/<int:user_id>')
# def approve_user(user_id):
#     user = User.query.get_or_404(user_id)
#     user.is_approved = True
#     db.session.commit()
#     return redirect(url_for('admin.dashboard'))


# # =========================================================
# # REJECT / DELETE USER
# # =========================================================
# @admin_bp.route('/reject/<int:user_id>')
# def reject_user(user_id):
#     user = User.query.get_or_404(user_id)
#     db.session.delete(user)
#     db.session.commit()
#     return redirect(url_for('admin.dashboard'))


# # =========================================================
# # ASSIGN CLASS / COURSE
# # =========================================================
# @admin_bp.route('/assign-class/<int:user_id>', methods=['POST'])
# def assign_class(user_id):
#     user = User.query.get_or_404(user_id)

#     class_id = request.form.get('class_id')

#     user.class_id = class_id
#     db.session.commit()

#     return redirect(url_for('admin.dashboard'))


# # =========================================================
# # VIEW ALL USERS
# # =========================================================
# @admin_bp.route('/users')
# def all_users():
#     users = User.query.all()
#     return render_template('admin/users.html', users=users)


# # =========================================================
# # REPORTS PAGE (placeholder)
# # =========================================================
# @admin_bp.route('/reports')
# def reports():
#     return render_template('admin/reports.html')


from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app import db
from app.models.user_model import User
from app.models.class_model import Class
from app.models.attendance_model import AttendanceRecord, AttendanceSession
from datetime import datetime, timezone

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# =========================================================
# AUTH GUARD
# =========================================================

def admin_required():
    """Returns a redirect if the session user is not an admin, else None."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard.dashboard'))
    return None


# =========================================================
# DASHBOARD
# =========================================================

@admin_bp.route('/dashboard')
def dashboard():
    guard = admin_required()
    if guard:
        return guard

    pending_users = User.query.filter_by(is_approved=False).all()
    teachers      = User.query.filter_by(role='teacher', is_approved=True).all()
    students      = User.query.filter_by(role='student', is_approved=True).all()
    classes       = Class.query.order_by(Class.name).all()

    return render_template(
        'admin/dashboard.html',
        pending_users=pending_users,
        teachers=teachers,
        students=students,
        classes=classes,
    )


# =========================================================
# APPROVE USER
# =========================================================

@admin_bp.route('/approve/<int:user_id>')
def approve_user(user_id):
    guard = admin_required()
    if guard:
        return guard

    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    return redirect(url_for('admin.dashboard'))


# =========================================================
# REJECT / DELETE USER
# =========================================================

@admin_bp.route('/reject/<int:user_id>')
def reject_user(user_id):
    guard = admin_required()
    if guard:
        return guard

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin.dashboard'))


# =========================================================
# ASSIGN CLASS TO TEACHER  →  sets Class.teacher_id
# ASSIGN CLASS TO STUDENT  →  sets User.class_id
# Both handled via one route, branching on the user's role
# =========================================================

@admin_bp.route('/assign-class/<int:user_id>', methods=['POST'])
def assign_class(user_id):
    guard = admin_required()
    if guard:
        return guard

    user     = User.query.get_or_404(user_id)
    class_id = request.form.get('class_id', type=int)

    if not class_id:
        return redirect(url_for('admin.dashboard'))

    target_class = Class.query.get_or_404(class_id)

    if user.role == 'teacher':
        # Wire the class to this teacher
        target_class.teacher_id = user.id
    else:
        # Assign the student to a class
        user.class_id = class_id

    db.session.commit()
    return redirect(url_for('admin.dashboard'))


# =========================================================
# VIEW ALL USERS
# =========================================================

@admin_bp.route('/users')
def all_users():
    guard = admin_required()
    if guard:
        return guard

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


# =========================================================
# REPORTS
# =========================================================

@admin_bp.route('/reports')
def reports():
    guard = admin_required()
    if guard:
        return guard

    # Overall totals
    total_records = AttendanceRecord.query.count()
    present_count = AttendanceRecord.query.filter_by(status='present').count()
    absent_count  = AttendanceRecord.query.filter_by(status='absent').count()
    rate = round((present_count / total_records) * 100, 2) if total_records else 0

    # Per-class breakdown
    classes = Class.query.order_by(Class.name).all()
    class_stats = []
    for cls in classes:
        # All sessions for this class
        session_ids = [s.id for s in cls.attendance_sessions]
        if not session_ids:
            continue

        cls_total   = AttendanceRecord.query.filter(
            AttendanceRecord.session_id.in_(session_ids)
        ).count()
        cls_present = AttendanceRecord.query.filter(
            AttendanceRecord.session_id.in_(session_ids),
            AttendanceRecord.status == 'present'
        ).count()
        cls_rate = round((cls_present / cls_total) * 100, 2) if cls_total else 0

        class_stats.append({
            'name':    cls.name,
            'code':    cls.code,
            'total':   cls_total,
            'present': cls_present,
            'absent':  cls_total - cls_present,
            'rate':    cls_rate,
        })

    # 10 most recent records
    recent = (
        AttendanceRecord.query
        .order_by(AttendanceRecord.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        'admin/reports.html',
        total_records=total_records,
        present_count=present_count,
        absent_count=absent_count,
        attendance_rate=rate,
        class_stats=class_stats,
        recent_records=recent,
    )