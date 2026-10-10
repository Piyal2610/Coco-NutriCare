import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User
from itsdangerous import URLSafeTimedSerializer, BadSignature
from app.mailer import send_email

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


RESET_MAX_AGE = 1800


def reset_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")


def make_reset_token(user):
    return reset_serializer().dumps({"id": user.id, "h": user.password_hash[-12:]})


def load_reset_user(token):
    try:
        data = reset_serializer().loads(token, max_age=RESET_MAX_AGE)
    except BadSignature:
        return None
    user = db.session.get(User, data.get("id"))
    if user is None or user.password_hash[-12:] != data.get("h"):
        return None
    return user


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            link = url_for("auth.reset_password", token=make_reset_token(user), _external=True)
            body = (
                f"Hello {user.name},\n\n"
                "Click the link below to reset your Coco NutriCare password. "
                "The link expires in 30 minutes.\n\n"
                f"{link}\n\n"
                "If you did not ask for this, you can ignore this email."
            )
            send_email(user.email, "Reset your Coco NutriCare password", body)
        flash("If that email is registered, a reset link has been sent.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html")


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = load_reset_user(token)
    if user is None:
        flash("This reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            user.set_password(password)
            db.session.commit()
            flash("Your password has been reset. Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html")