from flask import Blueprint, render_template, session, request, redirect, url_for
import random
import string
import re

from werkzeug.security import generate_password_hash, check_password_hash
from app.models.user_model import User
from app.database.extensions import db

auth_bp = Blueprint('auth', __name__)


# ======================
# UNIQUE ID GENERATOR
# ======================
def generate_unique_id():
    return "ATT-" + ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=7)
    )


# ======================
# PASSWORD STRENGTH CHECK
# ======================
def get_password_error(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return "Password must include at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return "Password must include at least one lowercase letter."
    if not re.search(r'[0-9]', password):
        return "Password must include at least one number."
    if not re.search(r'[^A-Za-z0-9]', password):
        return "Password must include at least one special character."
    return None


# ======================
# SIGNUP ROUTE
# ======================
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():

    error = None

    if request.method == 'POST':

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'student')

        if not name or not email or not password or not confirm_password:
            error = "All fields are required."
            return render_template('auth/signup.html', error=error)

        pw_error = get_password_error(password)
        if pw_error:
            error = pw_error
            return render_template('auth/signup.html', error=error)

        if password != confirm_password:
            error = "Passwords do not match."
            return render_template('auth/signup.html', error=error)

        if role not in ('student', 'teacher', 'admin'):
            error = "Invalid role selected."
            return render_template('auth/signup.html', error=error)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            error = "Account already exists. Please login instead."
            return render_template('auth/signup.html', error=error)

        hashed_password = generate_password_hash(password)
        unique_id = generate_unique_id()

        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            unique_id=unique_id,
            role=role,
            is_approved=True
        )

        db.session.add(new_user)
        db.session.commit()

        # auto-login right after signup — no separate login step needed
        session['user_id'] = new_user.id
        session['email'] = new_user.email
        session['role'] = new_user.role
        session['unique_id'] = new_user.unique_id

        return redirect(url_for('dashboard.dashboard'))

    return render_template('auth/signup.html', error=error)


# ======================
# LOGIN ROUTE
# ======================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    error = None

    if request.method == 'POST':

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            error = "Email and password are required."
            return render_template('auth/login.html', error=error)

        user = User.query.filter_by(email=email).first()

        if not user:
            error = "No account found with that email."
            return render_template('auth/login.html', error=error)

        if not check_password_hash(user.password, password):
            error = "Incorrect password."
            return render_template('auth/login.html', error=error)

        session['user_id'] = user.id
        session['email'] = user.email
        session['role'] = user.role
        session['unique_id'] = user.unique_id

        return redirect(url_for('dashboard.dashboard'))

    return render_template('auth/login.html', error=error)


# ======================
# LOGOUT ROUTE
# ======================
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))