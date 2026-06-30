from datetime import datetime, timedelta, timezone
from collections import defaultdict
import json
from flask import Blueprint, render_template, session as flask_session, redirect, url_for, request, jsonify, make_response
from app.models import AttendanceRecord, AttendanceSession, User
from io import BytesIO

try:
    import pdfkit
    pdfkit_config = pdfkit.configuration()
except (ImportError, OSError):
    pdfkit = None
    pdfkit_config = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    reportlab_available = True
except ImportError:
    reportlab_available = False

from app import db
from app.models.student_model import Class

dashboard_bp = Blueprint('dashboard', __name__)


# =========================================================
# TIME HELPERS
# =========================================================

def _now():
    return datetime.now(timezone.utc)


def _time_ago(dt):
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = _now() - dt
    if delta < timedelta(minutes=1):
        return "Just now"
    if delta < timedelta(hours=1):
        mins = int(delta.total_seconds() // 60)
        return f"{mins} min ago"
    if delta < timedelta(days=1):
        hrs = int(delta.total_seconds() // 3600)
        return f"{hrs} hr ago"
    if delta < timedelta(days=2):
        return "Yesterday"
    return dt.strftime("%b %d")


# =========================================================
# CHART BUILDER
# =========================================================

def _build_chart_data(records, mode="week"):
    today = _now().date()
    if mode == "day":
        days = 1
    elif mode == "month":
        days = 30
    else:
        days = 7
    date_range = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    stats = defaultdict(lambda: {"present": 0, "total": 0})
    for r in records:
        if not getattr(r, "created_at", None):
            continue
        d = r.created_at.date()
        if d in date_range:
            stats[d]["total"] += 1
            if r.status == "present":
                stats[d]["present"] += 1
    labels = []
    values = []
    for d in date_range:
        labels.append(d.strftime("%a") if mode != "month" else d.strftime("%d"))
        bucket = stats[d]
        if bucket["total"] == 0:
            values.append(0)
        else:
            values.append(round(bucket["present"] / bucket["total"] * 100))
    return {"labels": labels, "values": values}


# =========================================================
# DASHBOARD
# =========================================================

@dashboard_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))

    role    = flask_session.get('role', 'student')
    user_id = flask_session.get('user_id')

    user = db.session.get(User, user_id)
    if not user:
        flask_session.clear()
        return redirect(url_for('auth.login'))

    if role == "student":
        records  = AttendanceRecord.query.filter_by(student_id=user_id).all()
        template = "dashboard/student_dashboard.html"
    else:
        records  = AttendanceRecord.query.all()
        template = "dashboard/admin_teacher_dashboard.html"

    total   = len(records)
    present = sum(1 for r in records if r.status == "present")
    absent  = sum(1 for r in records if r.status == "absent")
    attendance_rate = round((present / total) * 100, 2) if total else 0

    chart_data = _build_chart_data(records, mode="week")

    notifications      = []
    recent_activity    = []
    active_classes_count = 0
    late_arrivals_count  = 0

    if role != "student":
        active_classes_count = db.session.query(AttendanceSession.class_id)\
            .filter(AttendanceSession.date == _now().date())\
            .distinct().count()

        late_arrivals_count = 0
        for r in records:
            if not r.session:
                continue
            if not r.sign_in_time or not r.session.start_time or not r.session.date:
                continue
            try:
                scheduled = datetime.combine(
                    r.session.date, r.session.start_time
                ).replace(tzinfo=timezone.utc)
                sign_in = r.sign_in_time
                if sign_in.tzinfo is None:
                    sign_in = sign_in.replace(tzinfo=timezone.utc)
                if (sign_in - scheduled) > timedelta(minutes=10):
                    late_arrivals_count += 1
            except Exception:
                continue

        for r in sorted(records, key=lambda x: x.created_at or _now(), reverse=True)[:6]:
            status = "positive" if r.status == "present" else "negative"
            recent_activity.append({
                "status":   status,
                "text":     f"{r.student_name} marked {r.status}",
                "time_ago": _time_ago(r.created_at)
            })

        if absent > 0:
            notifications.append({
                "type":     "danger",
                "title":    f"{absent} absences recorded",
                "subtitle": "Check attendance logs",
                "time":     "Today"
            })

    # student-specific data
    weekly = []
    if role == "student":
        days_of_week = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        today = _now().date()
        start_of_week = today - timedelta(days=today.weekday())
        for i, day_name in enumerate(days_of_week):
            day_date = start_of_week + timedelta(days=i)
            rec = next(
                (r for r in records if r.created_at and r.created_at.date() == day_date),
                None
            )
            weekly.append({
                "name":   day_name,
                "status": rec.status if rec else "absent"
            })

    return render_template(
        template,
        user                 = user,
        role                 = role,
        total_records        = total,
        present_count        = present,
        absent_count         = absent,
        attendance_rate      = attendance_rate,
        chart_data           = chart_data,
        chart_js             = json.dumps({"labels": list(chart_data["labels"]), "values": list(chart_data["values"])}),
        notifications        = notifications,
        notification_count   = len(notifications),
        recent_activity      = recent_activity,
        active_classes_count = active_classes_count,
        late_arrivals_count  = late_arrivals_count,
        active_page          = "dashboard",
        current_year         = _now().year,
        records              = records,
        weekly               = weekly if role == "student" else [],
    )


# =========================================================
# REAL-TIME DATA API
# =========================================================

@dashboard_bp.route('/dashboard/data')
def dashboard_data():
    if 'user_id' not in flask_session:
        return jsonify({"error": "unauthorized"}), 401

    mode    = request.args.get("mode", "week")
    from_dt = request.args.get("from")
    to_dt   = request.args.get("to")
    user_id = flask_session.get("user_id")
    role    = flask_session.get("role", "student")

    if role == "student":
        records = AttendanceRecord.query.filter_by(student_id=user_id).all()
    else:
        records = AttendanceRecord.query.all()

    if from_dt and to_dt:
        try:
            from_date = datetime.strptime(from_dt, "%Y-%m-%d").date()
            to_date   = datetime.strptime(to_dt,   "%Y-%m-%d").date()
            records   = [r for r in records if r.created_at and from_date <= r.created_at.date() <= to_date]
        except ValueError:
            pass

    chart = _build_chart_data(records, mode)
    return jsonify({
        "chart":   chart,
        "total":   len(records),
        "present": sum(1 for r in records if r.status == "present"),
        "absent":  sum(1 for r in records if r.status == "absent"),
    })


# =========================================================
# SEARCH
# =========================================================

@dashboard_bp.route('/search')
def search():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"results": []})

    users   = User.query.filter(User.name.ilike(f"%{query}%")).limit(5).all()
    records = AttendanceRecord.query.filter(
        AttendanceRecord.student_name.ilike(f"%{query}%")
    ).limit(5).all()

    return jsonify({
        "results": [
            *[{"type": "user",       "label": f"{u.name} · {u.role}",          "href": url_for('dashboard.dashboard')} for u in users],
            *[{"type": "attendance", "label": f"{r.student_name} — {r.status}", "href": url_for('dashboard.dashboard')} for r in records]
        ]
    })


# =========================================================
# ATTENDANCE PERCENTAGE
# =========================================================

@dashboard_bp.route('/dashboard/attendance-percentage')
def attendance_percentage():
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))
    return render_template(
        "dashboard/attendance_percentage.html",
        active_page="attendance_percentage"
    )


# =========================================================
# CLASSES CREATED
# =========================================================

@dashboard_bp.route('/dashboard/classes-created')
def classes_created():
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))
    sessions = AttendanceSession.query.order_by(AttendanceSession.created_at.desc()).all()
    return render_template(
        "dashboard/classes_created.html",
        sessions    = sessions,
        active_page = "classes"
    )


# =========================================================
# START SESSION
# =========================================================

@dashboard_bp.route('/dashboard/start-session', methods=['GET', 'POST'])
def start_session():
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))

    role = flask_session.get('role')
    if role not in ('admin', 'teacher'):
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        class_id = request.form.get('class_id')
        date_str = request.form.get('date')
        time_str = request.form.get('start_time')
        location = request.form.get('location', '').strip() or None

        if not class_id or not date_str or not time_str:
            classes = Class.query.order_by(Class.name).all()
            return render_template(
                'dashboard/start_session.html',
                classes    = classes,
                today      = _now().date().isoformat(),
                now_time   = _now().strftime('%H:%M'),
                error      = "All required fields must be filled.",
                active_page= "start"
            )

        session_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        session_time = datetime.strptime(time_str, '%H:%M').time()

        new_att_session = AttendanceSession(
            class_id   = int(class_id),
            teacher_id = flask_session.get('user_id'),
            date       = session_date,
            start_time = session_time,
            location   = location
        )
        db.session.add(new_att_session)
        db.session.commit()

        return redirect(url_for('dashboard.mark_attendance_session',
                                session_id=new_att_session.id))

    classes = Class.query.order_by(Class.name).all()
    return render_template(
        'dashboard/start_session.html',
        classes    = classes,
        today      = _now().date().isoformat(),
        now_time   = _now().strftime('%H:%M'),
        active_page= "start"
    )


# =========================================================
# MARK ATTENDANCE
# =========================================================

@dashboard_bp.route('/dashboard/mark-attendance/<int:session_id>', methods=['GET', 'POST'])
def mark_attendance_session(session_id):
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))

    role = flask_session.get('role')
    if role not in ('admin', 'teacher'):
        return redirect(url_for('dashboard.dashboard'))

    att_session = db.session.get(AttendanceSession, session_id)
    if not att_session:
        return redirect(url_for('dashboard.sessions'))

    students = User.query.filter_by(
        role     = 'student',
        class_id = att_session.class_id
    ).order_by(User.name).all()

    existing_records = AttendanceRecord.query.filter_by(session_id=session_id).all()
    existing = {r.student_id: r for r in existing_records}

    if request.method == 'POST':
        now = _now()
        for student in students:
            status   = request.form.get(f'status_{student.id}', 'absent')
            time_str = request.form.get(f'sign_in_{student.id}', '')

            sign_in_dt = None
            if time_str:
                try:
                    t = datetime.strptime(time_str, '%H:%M').time()
                    sign_in_dt = datetime.combine(att_session.date, t).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            if student.id in existing:
                rec              = existing[student.id]
                rec.status       = status
                rec.sign_in_time = sign_in_dt
            else:
                rec = AttendanceRecord(
                    session_id   = session_id,
                    student_id   = student.id,
                    student_name = student.name,
                    status       = status,
                    sign_in_time = sign_in_dt,
                    created_at   = now
                )
                db.session.add(rec)

        db.session.commit()
        existing_records = AttendanceRecord.query.filter_by(session_id=session_id).all()
        existing = {r.student_id: r for r in existing_records}

        return render_template(
            'dashboard/mark_attendance.html',
            att_session = att_session,
            students    = students,
            existing    = existing,
            now_time    = _now().strftime('%H:%M'),
            message     = "Attendance saved successfully.",
            active_page = "mark_attendance"
        )

    return render_template(
        'dashboard/mark_attendance.html',
        att_session = att_session,
        students    = students,
        existing    = existing,
        now_time    = _now().strftime('%H:%M'),
        active_page = "mark_attendance"
    )


# =========================================================
# SESSIONS LIST
# =========================================================

@dashboard_bp.route('/dashboard/sessions')
def sessions():
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))

    all_sessions = AttendanceSession.query.order_by(AttendanceSession.date.desc()).all()
    return render_template(
        'dashboard/classes_created.html',
        sessions    = all_sessions,
        active_page = "sessions"
    )


# =========================================================
# DELETE SESSION
# =========================================================

@dashboard_bp.route('/dashboard/sessions/<int:session_id>/delete', methods=['POST'])
def delete_session(session_id):
    if 'user_id' not in flask_session:
        return jsonify({"error": "unauthorized"}), 401

    role = flask_session.get('role')
    if role not in ('admin', 'teacher'):
        return jsonify({"error": "forbidden"}), 403

    att_session = db.session.get(AttendanceSession, session_id)
    if not att_session:
        return jsonify({"error": "Session not found"}), 404

    try:
        AttendanceRecord.query.filter_by(session_id=session_id).delete()
        db.session.delete(att_session)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# =========================================================
# EXPORT PDF
# =========================================================

@dashboard_bp.route('/dashboard/export-pdf')
def export_pdf():
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))

    role = flask_session.get('role')
    if role not in ('admin', 'teacher'):
        return redirect(url_for('dashboard.dashboard'))

    if not reportlab_available:
        return "ReportLab not installed. Run: pip install reportlab", 500

    classes = Class.query.order_by(Class.name).all()
    buffer  = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize     = A4,
        rightMargin  = 1.5 * cm,
        leftMargin   = 1.5 * cm,
        topMargin    = 1.5 * cm,
        bottomMargin = 1.5 * cm,
    )

    styles  = getSampleStyleSheet()
    DARK    = colors.HexColor('#0d2137')
    BLUE    = colors.HexColor('#4f8dff')
    LIGHT   = colors.HexColor('#8ab4d4')
    WHITE   = colors.white
    ROW_ALT = colors.HexColor('#f0f4f8')

    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=20, textColor=DARK, alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                     fontSize=9, textColor=LIGHT, alignment=TA_CENTER, spaceAfter=2)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'],
                                    fontSize=13, textColor=DARK, spaceBefore=14, spaceAfter=4)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, textColor=LIGHT)

    story = []

    story.append(Paragraph("AttendanceMS", title_style))
    story.append(Paragraph("Per-Class Attendance Summary Report", subtitle_style))
    story.append(Paragraph(f"Generated: {_now().strftime('%B %d, %Y at %I:%M %p UTC')}", subtitle_style))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE))
    story.append(Spacer(1, 0.4 * cm))

    if not classes:
        story.append(Paragraph("No classes found.", styles['Normal']))
    else:
        for cls in classes:
            story.append(Paragraph(f"{cls.name}  ({cls.code})", section_style))
            teacher_name = cls.teacher.name if cls.teacher else "Not assigned"
            story.append(Paragraph(f"Teacher: {teacher_name}", label_style))
            story.append(Spacer(1, 0.25 * cm))

            students = User.query.filter_by(role='student', class_id=cls.id).order_by(User.name).all()

            if not students:
                story.append(Paragraph("No students assigned to this class.", label_style))
                story.append(Spacer(1, 0.4 * cm))
                continue

            table_data = [["Student Name", "Student ID", "Present", "Absent", "Late", "Total", "Rate"]]
            class_present = class_absent = class_late = class_total = 0

            for student in students:
                records = AttendanceRecord.query.join(AttendanceSession).filter(
                    AttendanceRecord.student_id == student.id,
                    AttendanceSession.class_id  == cls.id
                ).all()

                present = sum(1 for r in records if r.status == 'present')
                absent  = sum(1 for r in records if r.status == 'absent')
                late    = sum(1 for r in records if r.status == 'late')
                total   = len(records)
                rate    = f"{round((present / total) * 100)}%" if total else "—"

                class_present += present
                class_absent  += absent
                class_late    += late
                class_total   += total

                table_data.append([
                    student.name, student.unique_id or "—",
                    str(present), str(absent), str(late), str(total), rate
                ])

            class_rate = f"{round((class_present / class_total) * 100)}%" if class_total else "—"
            table_data.append(["TOTAL", "", str(class_present), str(class_absent),
                                str(class_late), str(class_total), class_rate])

            col_widths = [5.5*cm, 2.5*cm, 1.8*cm, 1.8*cm, 1.8*cm, 1.8*cm, 2*cm]
            tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
            tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0),  (-1, 0),  DARK),
                ('TEXTCOLOR',     (0, 0),  (-1, 0),  WHITE),
                ('FONTNAME',      (0, 0),  (-1, 0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0, 0),  (-1, 0),  9),
                ('ALIGN',         (0, 0),  (-1, 0),  'CENTER'),
                ('BOTTOMPADDING', (0, 0),  (-1, 0),  8),
                ('TOPPADDING',    (0, 0),  (-1, 0),  8),
                ('FONTNAME',      (0, 1),  (-1, -2), 'Helvetica'),
                ('FONTSIZE',      (0, 1),  (-1, -2), 8.5),
                ('ALIGN',         (2, 1),  (-1, -2), 'CENTER'),
                ('ROWBACKGROUNDS',(0, 1),  (-1, -2), [WHITE, ROW_ALT]),
                ('TOPPADDING',    (0, 1),  (-1, -2), 6),
                ('BOTTOMPADDING', (0, 1),  (-1, -2), 6),
                ('BACKGROUND',    (0, -1), (-1, -1), colors.HexColor('#e8f0fe')),
                ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE',      (0, -1), (-1, -1), 8.5),
                ('ALIGN',         (2, -1), (-1, -1), 'CENTER'),
                ('TOPPADDING',    (0, -1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 7),
                ('GRID',          (0, 0),  (-1, -1), 0.4, colors.HexColor('#c5d5e8')),
                ('LINEBELOW',     (0, 0),  (-1, 0),  1.2, BLUE),
                ('LINEABOVE',     (0, -1), (-1, -1), 1,   BLUE),
                ('BOX',           (0, 0),  (-1, -1), 1,   BLUE),
            ]))

            story.append(tbl)
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph(
                f"<font color='#2ecc71'>✓ {class_present} present</font> &nbsp;&nbsp;"
                f"<font color='#e74c3c'>✗ {class_absent} absent</font> &nbsp;&nbsp;"
                f"<font color='#f39c12'>⏰ {class_late} late</font> &nbsp;&nbsp;"
                f"Overall rate: <b>{class_rate}</b>",
                ParagraphStyle('stat', parent=styles['Normal'], fontSize=8.5,
                               textColor=colors.HexColor('#4a6a8a'), spaceAfter=6)
            ))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#1e3a5f')))
            story.append(Spacer(1, 0.3 * cm))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "© AttendanceMS — Confidential. For internal use only.",
        ParagraphStyle('footer', parent=styles['Normal'], fontSize=7.5,
                       textColor=LIGHT, alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)

    filename = f"attendance_report_{_now().strftime('%Y%m%d_%H%M')}.pdf"
    response = make_response(buffer.read())
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# =========================================================
# STUDENTS REGISTERED
# =========================================================

@dashboard_bp.route('/dashboard/students-registered')
def students_registered():
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))

    role = flask_session.get('role')
    if role not in ('admin', 'teacher'):
        return redirect(url_for('dashboard.dashboard'))

    message = request.args.get('message')

    students = User.query.filter_by(role='student').order_by(User.name).all()
    classes  = Class.query.order_by(Class.name).all()

    attendance_rates = {}
    for student in students:
        records = AttendanceRecord.query.filter_by(student_id=student.id).all()
        total   = len(records)
        present = sum(1 for r in records if r.status == 'present')
        attendance_rates[student.id] = round((present / total) * 100) if total else 0

    return render_template(
        'dashboard/students_registered.html',
        students         = students,
        classes          = classes,
        attendance_rates = attendance_rates,
        message          = message,
        active_page      = 'students',
        current_year     = _now().year
    )


# =========================================================
# ASSIGN STUDENT TO CLASS
# =========================================================

@dashboard_bp.route('/dashboard/students/<int:student_id>/assign-class', methods=['POST'])
def assign_student_class(student_id):
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))

    role = flask_session.get('role')
    if role not in ('admin', 'teacher'):
        return redirect(url_for('dashboard.dashboard'))

    student  = db.session.get(User, student_id)
    class_id = request.form.get('class_id')

    if student:
        student.class_id = int(class_id) if class_id else None
        db.session.commit()

    return redirect(url_for('dashboard.students_registered') + '?message=Class+assignment+updated.')


# =========================================================
# MANAGE CLASSES
# =========================================================

@dashboard_bp.route('/dashboard/classes')
def manage_classes():
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))

    classes      = Class.query.order_by(Class.name).all()
    all_students = User.query.filter_by(role='student').order_by(User.name).all()

    return render_template(
        'dashboard/manage_classes.html',
        classes      = classes,
        all_students = all_students,
        active_page  = 'classes',
        current_year = _now().year
    )


# =========================================================
# CREATE CLASS
# =========================================================

@dashboard_bp.route('/dashboard/classes/create', methods=['POST'])
def create_class():
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))

    name = request.form.get('name', '').strip()
    code = request.form.get('code', '').strip().upper()

    if not name or not code:
        classes      = Class.query.order_by(Class.name).all()
        all_students = User.query.filter_by(role='student').order_by(User.name).all()
        return render_template(
            'dashboard/manage_classes.html',
            classes      = classes,
            all_students = all_students,
            error        = 'Class name and code are required.',
            active_page  = 'classes',
            current_year = _now().year
        )

    if Class.query.filter_by(code=code).first():
        classes      = Class.query.order_by(Class.name).all()
        all_students = User.query.filter_by(role='student').order_by(User.name).all()
        return render_template(
            'dashboard/manage_classes.html',
            classes      = classes,
            all_students = all_students,
            error        = f'Class code "{code}" already exists.',
            active_page  = 'classes',
            current_year = _now().year
        )

    new_class = Class(name=name, code=code)
    db.session.add(new_class)
    db.session.commit()

    return redirect(url_for('dashboard.manage_classes',
                            message=f'Class "{name}" created successfully.'))


# =========================================================
# DELETE CLASS
# =========================================================

@dashboard_bp.route('/dashboard/classes/<int:class_id>/delete', methods=['POST'])
def delete_class(class_id):
    if 'user_id' not in flask_session:
        return jsonify({"error": "unauthorized"}), 401

    role = flask_session.get('role')
    if role not in ('admin', 'teacher'):
        return jsonify({"error": "forbidden"}), 403

    cls = db.session.get(Class, class_id)
    if not cls:
        return jsonify({"error": "Class not found"}), 404

    try:
        User.query.filter_by(class_id=class_id).update({'class_id': None})
        session_ids = [s.id for s in AttendanceSession.query.filter_by(class_id=class_id).all()]
        if session_ids:
            AttendanceRecord.query.filter(
                AttendanceRecord.session_id.in_(session_ids)
            ).delete(synchronize_session=False)
        AttendanceSession.query.filter_by(class_id=class_id).delete()
        db.session.delete(cls)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# =========================================================
# ASSIGN STUDENTS TO CLASS
# =========================================================

@dashboard_bp.route('/dashboard/classes/<int:class_id>/assign-students', methods=['POST'])
def assign_students_to_class(class_id):
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))

    cls         = db.session.get(Class, class_id)
    student_ids = request.form.getlist('student_ids')

    if cls:
        User.query.filter_by(class_id=class_id).update({'class_id': None})
        for sid in student_ids:
            student = db.session.get(User, int(sid))
            if student:
                student.class_id = class_id
        db.session.commit()

    return redirect(url_for('dashboard.manage_classes',
                            message='Students assigned successfully.'))


# =========================================================
# ACTIVE SESSION CHECK (student polls this)
# =========================================================

@dashboard_bp.route('/dashboard/active-session')
def active_session():
    if 'user_id' not in flask_session:
        return jsonify({"error": "unauthorized"}), 401

    user_id = flask_session.get('user_id')
    user    = db.session.get(User, user_id)

    if not user or not user.class_id:
        return jsonify({"active": False, "no_class": not user or not user.class_id})

    today       = _now().date()
    att_session = AttendanceSession.query.filter_by(
        class_id = user.class_id,
        date     = today
    ).order_by(AttendanceSession.created_at.desc()).first()

    if not att_session:
        return jsonify({"active": False})

    existing = AttendanceRecord.query.filter_by(
        session_id = att_session.id,
        student_id = user_id
    ).first()

    return jsonify({
        "active":         True,
        "session_id":     att_session.id,
        "class_name":     att_session.class_.name if att_session.class_ else "Class",
        "start_time":     att_session.start_time.strftime('%I:%M %p'),
        "location":       att_session.location or "",
        "already_marked": existing is not None,
        "my_status":      existing.status if existing else None
    })


# =========================================================
# STUDENT SELF-MARK ATTENDANCE
# =========================================================

@dashboard_bp.route('/dashboard/self-mark/<int:session_id>', methods=['POST'])
def self_mark_attendance(session_id):
    if 'user_id' not in flask_session:
        return jsonify({"error": "unauthorized"}), 401

    user_id     = flask_session.get('user_id')
    user        = db.session.get(User, user_id)
    att_session = db.session.get(AttendanceSession, session_id)

    if not user or not att_session:
        return jsonify({"error": "Invalid session"}), 400

    if user.class_id != att_session.class_id:
        return jsonify({"error": "You are not in this class"}), 403

    existing = AttendanceRecord.query.filter_by(
        session_id = session_id,
        student_id = user_id
    ).first()

    if existing:
        return jsonify({"success": True, "already_marked": True, "status": existing.status})

    now = _now()
    try:
        scheduled = datetime.combine(
            att_session.date, att_session.start_time
        ).replace(tzinfo=timezone.utc)
        status = "late" if (now - scheduled) > timedelta(minutes=10) else "present"
    except Exception:
        status = "present"

    record = AttendanceRecord(
        session_id   = session_id,
        student_id   = user_id,
        student_name = user.name,
        status       = status,
        sign_in_time = now,
        created_at   = now
    )
    db.session.add(record)
    db.session.commit()

    class_name = att_session.class_.name if att_session.class_ else "your class"
    return jsonify({
        "success":       True,
        "already_marked":False,
        "status":        status,
        "time":          now.strftime('%I:%M %p'),
        "class_name":    class_name,
        "student_name":  user.name,
        "notification":  f"{user.name} marked {'present' if status == 'present' else status} in {class_name}"
    })


# =========================================================
# LIVE NOTIFICATIONS
# =========================================================

@dashboard_bp.route('/dashboard/live-notifications')
def live_notifications():
    if 'user_id' not in flask_session:
        return jsonify({"error": "unauthorized"}), 401

    alerts = _build_alerts()
    urgent = len([a for a in alerts if a['type'] in ('absent', 'late')])
    return jsonify({
        "alerts": alerts[:20],
        "counts": {
            "total":   len(alerts),
            "absent":  sum(1 for a in alerts if a['type'] == 'absent'),
            "late":    sum(1 for a in alerts if a['type'] == 'late'),
            "present": sum(1 for a in alerts if a['type'] == 'present'),
            "session": sum(1 for a in alerts if a['type'] == 'session'),
            "urgent":  urgent
        }
    })


# =========================================================
# ALERTS DATA API
# =========================================================

@dashboard_bp.route('/dashboard/alerts-data')
def alerts_data():
    if 'user_id' not in flask_session:
        return jsonify({"error": "unauthorized"}), 401

    alerts = _build_alerts()
    return jsonify({
        "alerts": alerts,
        "counts": {
            "total":   len(alerts),
            "absent":  sum(1 for a in alerts if a['type'] == 'absent'),
            "late":    sum(1 for a in alerts if a['type'] == 'late'),
            "present": sum(1 for a in alerts if a['type'] == 'present'),
            "session": sum(1 for a in alerts if a['type'] == 'session'),
        }
    })


# =========================================================
# ALERT BUILDER
# =========================================================

def _build_alerts():
    records_with_time = []

    records = AttendanceRecord.query\
        .order_by(AttendanceRecord.created_at.desc())\
        .limit(50).all()

    for r in records:
        class_name = ""
        if r.session and r.session.class_:
            class_name = r.session.class_.name
        if r.status == 'absent':
            text = f"{r.student_name} was marked absent"
        elif r.status == 'late':
            text = f"{r.student_name} arrived late"
        else:
            text = f"{r.student_name} marked present"

        records_with_time.append((
            r.created_at or _now(),
            {"type": r.status, "text": text, "student_name": r.student_name,
             "class_name": class_name, "time_ago": _time_ago(r.created_at)}
        ))

    att_sessions = AttendanceSession.query\
        .order_by(AttendanceSession.created_at.desc())\
        .limit(10).all()

    for s in att_sessions:
        class_name = s.class_.name if s.class_ else "a class"
        teacher    = s.teacher.name if s.teacher else "A teacher"
        records_with_time.append((
            s.created_at or _now(),
            {"type": "session", "text": f"{teacher} started a session for {class_name}",
             "student_name": teacher, "class_name": class_name, "time_ago": _time_ago(s.created_at)}
        ))

    records_with_time.sort(
        key=lambda x: x[0] if x[0].tzinfo else x[0].replace(tzinfo=timezone.utc),
        reverse=True
    )
    return [item for _, item in records_with_time]


# =========================================================
# APPROVE STUDENTS PAGE
# =========================================================

@dashboard_bp.route('/dashboard/students/approval')
def approve_students():
    if 'user_id' not in flask_session:
        return redirect(url_for('auth.login'))

    role = flask_session.get('role')
    if role not in ('admin', 'teacher'):
        return redirect(url_for('dashboard.dashboard'))

    user = db.session.get(User, flask_session['user_id'])
    return render_template(
        'dashboard/approve_students.html',
        user         = user,
        active_page  = 'approve_students',
        current_year = _now().year
    )


# =========================================================
# PENDING STUDENTS API
# =========================================================

@dashboard_bp.route('/dashboard/pending-students')
def pending_students():
    if 'user_id' not in flask_session:
        return jsonify({"error": "unauthorized"}), 401

    role = flask_session.get('role')
    if role not in ('admin', 'teacher'):
        return jsonify({"error": "forbidden"}), 403

    users = User.query.filter(User.role.in_(['student', 'teacher']))\
                      .order_by(User.created_at.desc()).all()

    def user_status(u):
        return 'approved' if u.is_approved else 'pending'

    users_list = [
        {"id": u.id, "name": u.name, "email": u.email, "role": u.role,
         "unique_id": u.unique_id, "status": user_status(u),
         "created_at": u.created_at.isoformat() if u.created_at else None}
        for u in users
    ]

    pending  = sum(1 for u in users_list if u['status'] == 'pending')
    approved = sum(1 for u in users_list if u['status'] == 'approved')
    rejected = sum(1 for u in users_list if u['status'] == 'rejected')

    return jsonify({
        "users":  users_list,
        "counts": {"pending": pending, "approved": approved,
                   "rejected": rejected, "total": len(users_list)}
    })


# =========================================================
# APPROVE / REJECT STUDENTS
# =========================================================

@dashboard_bp.route('/dashboard/approve-students', methods=['POST'])
def approve_students_action():
    if 'user_id' not in flask_session:
        return jsonify({"error": "unauthorized"}), 401

    role = flask_session.get('role')
    if role not in ('admin', 'teacher'):
        return jsonify({"error": "forbidden"}), 403

    data   = request.get_json()
    ids    = data.get('ids', [])
    action = data.get('action')

    if not ids or action not in ('approved', 'rejected'):
        return jsonify({"success": False, "message": "Invalid request."}), 400

    users = User.query.filter(User.id.in_(ids)).all()
    for u in users:
        u.is_approved = (action == 'approved')
    db.session.commit()

    return jsonify({"success": True, "updated": len(users)})


# =========================================================
# PENDING APPROVALS COUNT
# =========================================================

@dashboard_bp.route('/dashboard/pending-approvals-count')
def pending_approvals_count():
    if 'user_id' not in flask_session:
        return jsonify({"count": 0})

    role = flask_session.get('role')
    if role not in ('admin', 'teacher'):
        return jsonify({"count": 0})

    count = User.query.filter(
        User.role.in_(['student', 'teacher']),
        User.is_approved == False
    ).count()

    return jsonify({"count": count})