from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Child, GrowthRecord
from app.models.child import GENDERS
from app.growth import weight_percentile, growth_trend, update_growth_records

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
            return redirect(url_for("parent.children"))
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
            update_growth_records(child)
            db.session.commit()
            flash(f"{child.name}'s profile has been updated.", "success")
            return redirect(url_for("parent.child_detail", child_id=child.id))
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
    return redirect(url_for("parent.children"))


@bp.route("/children")
@login_required
def children():
    parent_only()
    kids = Child.query.filter_by(parent_id=current_user.id).order_by(Child.name).all()
    return render_template("parent/children.html", children=kids)


@bp.route("/children/<int:child_id>")
@login_required
def child_detail(child_id):
    parent_only()
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    latest = child.growth_records[-1] if child.growth_records else None
    return render_template("parent/child_detail.html", child=child, latest=latest)


@bp.route("/children/<int:child_id>/growth/add", methods=["GET", "POST"])
@login_required
def add_growth_record(child_id):
    parent_only()
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    if request.method == "POST":
        date_text = request.form.get("date", "")
        weight_text = request.form.get("weight_kg", "")
        height_text = request.form.get("height_cm", "")

        errors = []
        try:
            record_date = datetime.strptime(date_text, "%Y-%m-%d").date()
            if record_date > date.today():
                errors.append("Measurement date cannot be in the future.")
            elif record_date < child.date_of_birth:
                errors.append("Measurement date cannot be before the date of birth.")
        except ValueError:
            errors.append("Please enter a valid measurement date.")
        try:
            weight = float(weight_text)
            if not 0.5 <= weight <= 150:
                errors.append("Weight must be between 0.5 and 150 kg.")
        except ValueError:
            errors.append("Please enter a valid weight.")
        try:
            height = float(height_text)
            if not 30 <= height <= 200:
                errors.append("Height must be between 30 and 200 cm.")
        except ValueError:
            errors.append("Please enter a valid height.")

        if errors:
            for error in errors:
                flash(error, "error")
        else:
            age_days = (record_date - child.date_of_birth).days
            percentile = weight_percentile(child.gender, age_days, weight)
            previous = next((r for r in reversed(child.growth_records) if r.date < record_date), None)
            trend = growth_trend(previous.percentile if previous else None, percentile)
            record = GrowthRecord(child=child, date=record_date, weight_kg=weight, height_cm=height, percentile=percentile, trend=trend)            
            db.session.add(record)
            db.session.commit()
            flash("Growth record saved.", "success")
            return redirect(url_for("parent.child_detail", child_id=child.id))
    return render_template("parent/growth_form.html", child=child, today=date.today().isoformat())