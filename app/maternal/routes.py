from datetime import date, datetime, time, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from app.extensions import db
from app.models import MaternalProfile, Consultation, Reminder, Recommendation
from app.nutrition import create_maternal_recommendation
from app.models.maternal_profile import MATERNAL_CONDITIONS
from app.models.consultation import CONSULTATION_REASONS
from app.decorators import role_required
from app.parent.routes import verified_doctors

bp = Blueprint("maternal", __name__, url_prefix="/maternal")

TRIMESTER_TIPS = {
    "First": [
        "Take folic acid and other supplements exactly as your doctor advises.",
        "Eat small, frequent meals if you feel nauseous and keep drinking water.",
        "Book your first antenatal check-up.",
    ],
    "Second": [
        "Include iron- and calcium-rich foods such as leafy greens, lentils, eggs, fish and milk.",
        "Stay lightly active, for example short walks, if your doctor agrees.",
        "Attend your mid-pregnancy scan and regular check-ups.",
    ],
    "Third": [
        "Contact your doctor quickly for severe headache, sudden swelling, bleeding or reduced baby movement.",
        "Rest on your side and keep eating small, balanced meals.",
        "Prepare your hospital bag and delivery plan.",
    ],
}

MATERNAL_REMINDER_TYPES = ("Medicine", "Checkup", "Vaccination", "Nutrition", "Other")
ANC_WEEKS = (12, 20, 26, 30, 34, 36, 38, 40)


@bp.route("/")
@role_required("mother")
def index():
    profile = current_user.maternal_profile
    if profile is None:
        flash("Please complete your maternal profile first.", "success")
        return redirect(url_for("maternal.edit_profile"))
    reminder_count = Reminder.query.filter_by(maternal_id=profile.id, status="Pending").count()
    consults = Consultation.query.filter_by(maternal_id=profile.id).order_by(Consultation.created_at.desc()).all()
    return render_template(
        "maternal/dashboard.html",
        profile=profile,
        tips=TRIMESTER_TIPS[profile.trimester],
        reminder_count=reminder_count,
        consults=consults,
    )


@bp.route("/profile", methods=["GET", "POST"])
@role_required("mother")
def edit_profile():
    profile = current_user.maternal_profile
    if request.method == "POST":
        due_text = request.form.get("due_date", "")
        conditions = [c for c in request.form.getlist("conditions") if c in MATERNAL_CONDITIONS]
        dietary_habits = request.form.get("dietary_habits", "").strip()
        today = date.today()
        try:
            due_date = datetime.strptime(due_text, "%Y-%m-%d").date()
        except ValueError:
            due_date = None
        if due_date is None:
            flash("Please enter a valid due date.", "error")
        elif not today - timedelta(days=14) <= due_date <= today + timedelta(days=280):
            flash("Due date must be within the next 40 weeks.", "error")
        else:
            if profile is None:
                profile = MaternalProfile(user_id=current_user.id, due_date=due_date)
                db.session.add(profile)
            profile.due_date = due_date
            profile.conditions = ",".join(conditions) or None
            profile.dietary_habits = dietary_habits or None
            db.session.commit()
            flash("Maternal profile saved.", "success")
            return redirect(url_for("maternal.index"))
    return render_template("maternal/profile_form.html", profile=profile, conditions=MATERNAL_CONDITIONS)


@bp.route("/consult", methods=["GET", "POST"])
@role_required("mother")
def request_consultation():
    profile = current_user.maternal_profile
    if profile is None:
        return redirect(url_for("maternal.edit_profile"))
    doctors = verified_doctors()
    if request.method == "POST":
        doctor_id = request.form.get("doctor_id", type=int)
        reason = request.form.get("reason", "")
        description = request.form.get("description", "").strip()
        doctor = next((d for d in doctors if d.id == doctor_id), None)
        if doctor is None:
            flash("Please choose a verified doctor.", "error")
        elif reason not in CONSULTATION_REASONS:
            flash("Please choose a reason.", "error")
        elif Consultation.query.filter(
            Consultation.maternal_id == profile.id,
            Consultation.doctor_id == doctor.id,
            Consultation.status.in_(["Pending", "Accepted"]),
        ).first():
            flash(f"You already have an open consultation with {doctor.name}.", "error")
        else:
            db.session.add(Consultation(
                requester_id=current_user.id,
                doctor_id=doctor.id,
                maternal_id=profile.id,
                reason=reason,
                description=description or None,
                created_at=datetime.now(),
            ))
            db.session.commit()
            flash(f"Consultation request sent to {doctor.name}.", "success")
            return redirect(url_for("maternal.index"))
    return render_template("maternal/consult_form.html", doctors=doctors, reasons=CONSULTATION_REASONS)
@bp.route("/nutrition")
@role_required("mother")
def nutrition():
    profile = current_user.maternal_profile
    if profile is None:
        return redirect(url_for("maternal.edit_profile"))
    rec = Recommendation.query.filter_by(maternal_id=profile.id).order_by(Recommendation.id.desc()).first()
    plan = rec.plan if rec else None
    if plan and plan.get("type") != "maternal":
        plan = None
    outdated = bool(plan) and (plan["conditions"] != profile.condition_labels or plan["trimester"] != profile.trimester)
    return render_template("maternal/nutrition.html", profile=profile, plan=plan, rec=rec, outdated=outdated)


@bp.route("/nutrition/regenerate", methods=["POST"])
@role_required("mother")
def regenerate_nutrition():
    profile = current_user.maternal_profile
    if profile is None:
        return redirect(url_for("maternal.edit_profile"))
    create_maternal_recommendation(profile)
    flash("A new nutrition plan has been generated.", "success")
    return redirect(url_for("maternal.nutrition"))


def mark_missed_maternal(profile):
    overdue = Reminder.query.filter(
        Reminder.maternal_id == profile.id,
        Reminder.status.in_(["Pending", "Snoozed"]),
        Reminder.scheduled_at < datetime.now(),
    ).all()
    for reminder in overdue:
        reminder.status = "Missed"
    if overdue:
        db.session.commit()


def read_maternal_reminder_form():
    reminder_type = request.form.get("type", "")
    title = request.form.get("title", "").strip()
    date_text = request.form.get("date", "")
    time_text = request.form.get("time", "")
    errors = []
    if reminder_type not in MATERNAL_REMINDER_TYPES:
        errors.append("Please choose a reminder type.")
    if not title:
        errors.append("Title is required.")
    try:
        scheduled_at = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
    except ValueError:
        scheduled_at = None
        errors.append("Please enter a valid date and time.")
    return {"type": reminder_type, "title": title, "scheduled_at": scheduled_at}, errors


def get_my_reminder(reminder_id):
    profile = current_user.maternal_profile
    if profile is None:
        abort(404)
    return Reminder.query.filter_by(id=reminder_id, maternal_id=profile.id).first_or_404()


@bp.route("/reminders")
@role_required("mother")
def reminders():
    profile = current_user.maternal_profile
    if profile is None:
        return redirect(url_for("maternal.edit_profile"))
    mark_missed_maternal(profile)
    selected_type = request.args.get("type", "All")
    query = Reminder.query.filter_by(maternal_id=profile.id)
    if selected_type in MATERNAL_REMINDER_TYPES:
        query = query.filter_by(type=selected_type)
    else:
        selected_type = "All"
    items = query.order_by(Reminder.scheduled_at).all()
    return render_template(
        "maternal/reminders.html",
        reminders=items,
        types=MATERNAL_REMINDER_TYPES,
        selected_type=selected_type,
        today=date.today(),
    )


@bp.route("/reminders/add", methods=["GET", "POST"])
@role_required("mother")
def add_reminder():
    profile = current_user.maternal_profile
    if profile is None:
        return redirect(url_for("maternal.edit_profile"))
    if request.method == "POST":
        data, errors = read_maternal_reminder_form()
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            db.session.add(Reminder(maternal_id=profile.id, **data))
            db.session.commit()
            flash("Reminder added.", "success")
            return redirect(url_for("maternal.reminders"))
    return render_template("maternal/reminder_form.html", reminder=None, types=MATERNAL_REMINDER_TYPES)


@bp.route("/reminders/<int:reminder_id>/edit", methods=["GET", "POST"])
@role_required("mother")
def edit_reminder(reminder_id):
    reminder = get_my_reminder(reminder_id)
    if request.method == "POST":
        data, errors = read_maternal_reminder_form()
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            for key, value in data.items():
                setattr(reminder, key, value)
            if reminder.status == "Missed" and reminder.scheduled_at > datetime.now():
                reminder.status = "Pending"
            db.session.commit()
            flash("Reminder updated.", "success")
            return redirect(url_for("maternal.reminders"))
    return render_template("maternal/reminder_form.html", reminder=reminder, types=MATERNAL_REMINDER_TYPES)


@bp.route("/reminders/<int:reminder_id>/delete", methods=["POST"])
@role_required("mother")
def delete_reminder(reminder_id):
    reminder = get_my_reminder(reminder_id)
    db.session.delete(reminder)
    db.session.commit()
    flash("Reminder deleted.", "success")
    return redirect(url_for("maternal.reminders"))


@bp.route("/reminders/<int:reminder_id>/status", methods=["POST"])
@role_required("mother")
def update_reminder_status(reminder_id):
    reminder = get_my_reminder(reminder_id)
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
        return redirect(url_for("maternal.reminders"))
    db.session.commit()
    return redirect(url_for("maternal.reminders"))


@bp.route("/reminders/antenatal", methods=["POST"])
@role_required("mother")
def add_antenatal_schedule():
    profile = current_user.maternal_profile
    if profile is None:
        return redirect(url_for("maternal.edit_profile"))
    existing = {r.title for r in Reminder.query.filter_by(maternal_id=profile.id, type="Checkup").all()}
    added = 0
    for week in ANC_WEEKS:
        when = datetime.combine(profile.due_date - timedelta(weeks=40 - week), time(10, 0))
        title = f"Antenatal check-up (week {week})"
        if when <= datetime.now() or title in existing:
            continue
        db.session.add(Reminder(maternal_id=profile.id, type="Checkup", title=title, scheduled_at=when))
        added += 1
    db.session.commit()
    if added:
        flash(f"{added} antenatal check-up reminders added.", "success")
    else:
        flash("Your upcoming antenatal check-ups are already scheduled.", "success")
    return redirect(url_for("maternal.reminders", type="Checkup"))