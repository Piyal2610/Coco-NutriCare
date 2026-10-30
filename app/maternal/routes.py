from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from app.extensions import db
from app.models import MaternalProfile, Consultation, Reminder
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