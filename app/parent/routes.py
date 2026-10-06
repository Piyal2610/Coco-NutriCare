from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Child
from app.models.child import GENDERS

bp = Blueprint("parent", __name__, url_prefix="/parent")


@bp.route("/")
@login_required
def index():
    return render_template("dashboard.html", section="Parent")


def parent_only():
    if current_user.role != "parent":
        abort(403)


def read_child_form():
    name = request.form.get("name", "").strip()
    dob_text = request.form.get("date_of_birth", "")
    gender = request.form.get("gender", "")
    dietary_habits = request.form.get("dietary_habits", "").strip()

    errors = []
    if not name:
        errors.append("Child name is required.")
    try:
        dob = datetime.strptime(dob_text, "%Y-%m-%d").date()
        if dob > date.today():
            errors.append("Date of birth cannot be in the future.")
    except ValueError:
        dob = None
        errors.append("Please enter a valid date of birth.")
    if gender not in GENDERS:
        errors.append("Please choose a gender.")

    data = {"name": name, "date_of_birth": dob, "gender": gender, "dietary_habits": dietary_habits}
    return data, errors


@bp.route("/children/add", methods=["GET", "POST"])
@login_required
def add_child():
    parent_only()
    if request.method == "POST":
        data, errors = read_child_form()
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            child = Child(parent=current_user, **data)
            db.session.add(child)
            db.session.commit()
            flash(f"{child.name} has been added.", "success")
            return redirect(url_for("parent.index"))
    return render_template("parent/child_form.html", child=None)


@bp.route("/children/<int:child_id>/edit", methods=["GET", "POST"])
@login_required
def edit_child(child_id):
    parent_only()
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    if request.method == "POST":
        data, errors = read_child_form()
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            for key, value in data.items():
                setattr(child, key, value)
            db.session.commit()
            flash(f"{child.name}'s profile has been updated.", "success")
            return redirect(url_for("parent.index"))
    return render_template("parent/child_form.html", child=child)


@bp.route("/children/<int:child_id>/delete", methods=["POST"])
@login_required
def delete_child(child_id):
    parent_only()
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    name = child.name
    db.session.delete(child)
    db.session.commit()
    flash(f"{name} has been removed.", "success")
    return redirect(url_for("parent.index"))