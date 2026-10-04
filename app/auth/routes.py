import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_ROLES = ("parent", "doctor", "mother")
ROLE_HOME = {
    "parent": "parent.index",
    "doctor": "doctor.index",
    "mother": "maternal.index",
    "admin": "admin.index",
}


@bp.route("/")
def index():
    return "Auth section is working!"


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        role = request.form.get("role", "")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Name, email and password are required.", "error")
        elif not EMAIL_RE.match(email):
            flash("Please enter a valid email address.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif role not in ALLOWED_ROLES:
            flash("Please choose a valid role.", "error")
        elif User.query.filter_by(email=email).first():
            flash("This email is already registered.", "error")
        else:
            user = User(name=name, email=email, phone=phone, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html")   


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(ROLE_HOME[current_user.role]))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            flash("Wrong email or password.", "error")
        elif not user.active:
            flash("Your account is deactivated. Please contact admin.", "error")
        else:
            login_user(user, remember=remember)
            flash(f"Welcome, {user.name}!", "success")
            return redirect(url_for(ROLE_HOME[user.role]))

    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
