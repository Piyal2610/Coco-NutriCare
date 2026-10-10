from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Child, GrowthRecord, Reminder, Consultation
from app.models.child import GENDERS
from app.models.reminder import REMINDER_TYPES
from app.growth import weight_percentile, growth_trend, update_growth_records, weight_at_z, growth_alert
from app.decorators import role_required

bp = Blueprint("parent", __name__, url_prefix="/parent")


@bp.route("/")
@role_required("parent")
def index():
    kids = Child.query.filter_by(parent_id=current_user.id).order_by(Child.name).all()
    child_rows = []
    for child in kids:
        latest = child.growth_records[-1] if child.growth_records else None
        child_rows.append({"child": child, "latest": latest, "alert": growth_alert(latest)})
    needs_review = sum(1 for row in child_rows if row["alert"])
    child_ids = [child.id for child in kids]
    reminder_count = Reminder.query.filter(Reminder.child_id.in_(child_ids), Reminder.status == "Pending").count()
    consultation_count = Consultation.query.filter(
        Consultation.requester_id == current_user.id,
        Consultation.status.in_(["Pending", "Accepted"]),
    ).count()
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    return render_template(
        "parent/dashboard.html",
        greeting=greeting,
        child_rows=child_rows,
        needs_review=needs_review,
        reminder_count=reminder_count,
        consultation_count=consultation_count,
    )





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
@role_required("parent")
def add_child():

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
@role_required("parent")
def edit_child(child_id):

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
@role_required("parent")
def delete_child(child_id):

    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    name = child.name
    db.session.delete(child)
    db.session.commit()
    flash(f"{name} has been removed.", "success")
    return redirect(url_for("parent.children"))


@bp.route("/children")
@role_required("parent")
def children():

    kids = Child.query.filter_by(parent_id=current_user.id).order_by(Child.name).all()
    return render_template("parent/children.html", children=kids)


@bp.route("/children/<int:child_id>")
@role_required("parent")
def child_detail(child_id):

    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    latest = child.growth_records[-1] if child.growth_records else None
    return render_template("parent/child_detail.html", child=child, latest=latest)


@bp.route("/children/<int:child_id>/growth/add", methods=["GET", "POST"])
@role_required("parent")
def add_growth_record(child_id):

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


@bp.route("/children/<int:child_id>/growth")
@role_required("parent")
def growth_tracking(child_id):

    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    records = child.growth_records
    latest = records[-1] if records else None
    chart = {"labels": [], "weights": [], "p3": [], "p50": [], "p97": []}
    for r in records:
        age_days = (r.date - child.date_of_birth).days
        chart["labels"].append(r.date.strftime("%b %d, %Y"))
        chart["weights"].append(r.weight_kg)
        chart["p3"].append(weight_at_z(child.gender, age_days, -1.881))
        chart["p50"].append(weight_at_z(child.gender, age_days, 0))
        chart["p97"].append(weight_at_z(child.gender, age_days, 1.881))
    return render_template("parent/growth.html", child=child, latest=latest, chart=chart, alert=growth_alert(latest))    


def read_reminder_form(kids):
    child_id = request.form.get("child_id", type=int)
    reminder_type = request.form.get("type", "")
    title = request.form.get("title", "").strip()
    date_text = request.form.get("date", "")
    time_text = request.form.get("time", "")

    errors = []
    if child_id not in [kid.id for kid in kids]:
        errors.append("Please choose a child.")
    if reminder_type not in REMINDER_TYPES:
        errors.append("Please choose a reminder type.")
    if not title:
        errors.append("Title is required.")
    try:
        scheduled_at = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
    except ValueError:
        scheduled_at = None
        errors.append("Please enter a valid date and time.")

    data = {"child_id": child_id, "type": reminder_type, "title": title, "scheduled_at": scheduled_at}
    return data, errors


def get_parent_reminder(reminder_id):
    return (
        Reminder.query.join(Child)
        .filter(Reminder.id == reminder_id, Child.parent_id == current_user.id)
        .first_or_404()
    )


@bp.route("/reminders")
@role_required("parent")
def reminders():
    mark_missed_reminders()

    items = (
        Reminder.query.join(Child)
        .filter(Child.parent_id == current_user.id)
        .order_by(Reminder.scheduled_at)
        .all()
    )
    return render_template("parent/reminders.html", reminders=items)


@bp.route("/reminders/add", methods=["GET", "POST"])
@role_required("parent")
def add_reminder():
    kids = Child.query.filter_by(parent_id=current_user.id).order_by(Child.name).all()
    if not kids:
        flash("Please add a child before creating reminders.", "error")
        return redirect(url_for("parent.add_child"))
    if request.method == "POST":
        data, errors = read_reminder_form(kids)
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            db.session.add(Reminder(**data))
            db.session.commit()
            flash("Reminder added.", "success")
            return redirect(url_for("parent.reminders"))
    return render_template("parent/reminder_form.html", reminder=None, kids=kids, types=REMINDER_TYPES)


@bp.route("/reminders/<int:reminder_id>/edit", methods=["GET", "POST"])
@role_required("parent")
def edit_reminder(reminder_id):
    reminder = get_parent_reminder(reminder_id)
    kids = Child.query.filter_by(parent_id=current_user.id).order_by(Child.name).all()
    if request.method == "POST":
        data, errors = read_reminder_form(kids)
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            for key, value in data.items():
                setattr(reminder, key, value)
            db.session.commit()
            flash("Reminder updated.", "success")
            return redirect(url_for("parent.reminders"))
    return render_template("parent/reminder_form.html", reminder=reminder, kids=kids, types=REMINDER_TYPES)


@bp.route("/reminders/<int:reminder_id>/delete", methods=["POST"])
@role_required("parent")
def delete_reminder(reminder_id):
    reminder = get_parent_reminder(reminder_id)
    db.session.delete(reminder)
    db.session.commit()
    flash("Reminder deleted.", "success")
    return redirect(url_for("parent.reminders"))   


def mark_missed_reminders():
    overdue = (
        Reminder.query.join(Child)
        .filter(
            Child.parent_id == current_user.id,
            Reminder.status.in_(["Pending", "Snoozed"]),
            Reminder.scheduled_at < datetime.now(),
        )
        .all()
    )
    for reminder in overdue:
        reminder.status = "Missed"
    if overdue:
        db.session.commit()


@bp.route("/reminders/<int:reminder_id>/status", methods=["POST"])
@role_required("parent")
def update_reminder_status(reminder_id):
    reminder = get_parent_reminder(reminder_id)
    action = request.form.get("action", "")
    if action == "complete":
        reminder.status = "Completed"
        flash(f"'{reminder.title}' marked as completed.", "success")
    elif action == "snooze":
        reminder.scheduled_at = max(reminder.scheduled_at, datetime.now()) + timedelta(days=1)
        reminder.status = "Snoozed"
        flash(f"'{reminder.title}' snoozed for 1 day.", "success")
    else:
        flash("Unknown action.", "error")
        return redirect(url_for("parent.reminders"))
    db.session.commit()
    return redirect(url_for("parent.reminders"))    