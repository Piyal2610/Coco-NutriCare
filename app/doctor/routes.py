from datetime import datetime
import re
from sqlalchemy import func, select
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from app.extensions import db
from app.models import DoctorProfile, Recommendation, Consultation, Child, Reminder
from app.models.consultation import CONSULTATION_STATUSES
from app.models.recommendation import REVIEW_STATUSES
from app.nutrition import cross_check
from app.growth import growth_alert
from app.decorators import role_required, verified_doctor_required

bp = Blueprint("doctor", __name__, url_prefix="/doctor")

SPECIALIZATIONS = ("Pediatrics", "Gynecology", "Nutrition", "General Practice")


@bp.route("/")
@verified_doctor_required
def index():
    return render_template("dashboard.html", section="Doctor")


@bp.route("/profile", methods=["GET", "POST"])
@role_required("doctor")
def complete_profile():
    profile = current_user.doctor_profile
    if profile and profile.verification_status != "Rejected":
        return redirect(url_for("doctor.pending"))
    if request.method == "POST":
        specialization = request.form.get("specialization", "")
        license_no = request.form.get("license_no", "").strip().upper()
        experience = request.form.get("experience_years", type=int)
        errors = []
        if specialization not in SPECIALIZATIONS:
            errors.append("Please choose a specialization.")
        if not re.fullmatch(r"[A-Z0-9-]{3,30}", license_no):
            errors.append("License number must be 3-30 letters, numbers or dashes.")
        elif DoctorProfile.query.filter(
            DoctorProfile.license_no == license_no,
            DoctorProfile.user_id != current_user.id,
        ).first():
            errors.append("This license number is already registered.")
        if experience is None or not 0 <= experience <= 60:
            errors.append("Experience must be between 0 and 60 years.")
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            if profile is None:
                profile = DoctorProfile(user_id=current_user.id)
                db.session.add(profile)
            profile.specialization = specialization
            profile.license_no = license_no
            profile.experience_years = experience
            profile.verification_status = "Pending"
            profile.rejection_reason = None
            profile.verified_at = None
            db.session.commit()
            flash("Profile submitted. An admin will verify your license.", "success")
            return redirect(url_for("doctor.pending"))
    return render_template("doctor/profile_form.html", profile=profile, specializations=SPECIALIZATIONS)


@bp.route("/pending")
@role_required("doctor")
def pending():
    profile = current_user.doctor_profile
    if profile is None:
        return redirect(url_for("doctor.complete_profile"))
    if profile.is_verified:
        return redirect(url_for("doctor.index"))
    return render_template("doctor/pending.html", profile=profile)


def latest_child_plans():
    latest_ids = (
        select(func.max(Recommendation.id))
        .where(Recommendation.child_id.is_not(None))
        .group_by(Recommendation.child_id)
    )
    return Recommendation.query.filter(Recommendation.id.in_(latest_ids))


@bp.route("/reviews")
@verified_doctor_required
def reviews():
    status = request.args.get("status", "Pending")
    if status not in REVIEW_STATUSES:
        status = "Pending"
    items = (
        latest_child_plans()
        .filter(Recommendation.review_status == status)
        .order_by(Recommendation.created_at)
        .all()
    )
    counts = {s: latest_child_plans().filter(Recommendation.review_status == s).count() for s in REVIEW_STATUSES}
    conflicts = {rec.id: cross_check(rec.plan, rec.child) for rec in items if rec.plan}
    return render_template(
        "doctor/reviews.html",
        items=items,
        status=status,
        counts=counts,
        statuses=REVIEW_STATUSES,
        conflicts=conflicts,
    )


@bp.route("/reviews/<int:rec_id>", methods=["POST"])
@verified_doctor_required
def review_plan(rec_id):
    rec = db.get_or_404(Recommendation, rec_id)
    action = request.form.get("action", "")
    note = request.form.get("note", "").strip()
    if action not in ("approve", "flag"):
        flash("Unknown action.", "error")
    elif action == "flag" and not note:
        flash("Please add a note explaining why the plan is flagged.", "error")
    elif action == "approve" and rec.plan and cross_check(rec.plan, rec.child):
        flash("This plan contains a known allergen and cannot be approved.", "error")
    else:
        rec.review_status = "Approved" if action == "approve" else "Flagged"
        rec.doctor_note = note or None
        rec.reviewed_by = current_user.id
        rec.reviewed_at = datetime.now()
        db.session.commit()
        flash(f"Plan for {rec.child.name} marked as {rec.review_status}.", "success")
    return redirect(url_for("doctor.reviews"))
@bp.route("/consultations")
@verified_doctor_required
def consultations():
    status = request.args.get("status", "Pending")
    if status not in CONSULTATION_STATUSES:
        status = "Pending"
    base = Consultation.query.filter_by(doctor_id=current_user.id)
    items = base.filter_by(status=status).order_by(Consultation.created_at).all()
    counts = {s: base.filter_by(status=s).count() for s in CONSULTATION_STATUSES}
    return render_template(
        "doctor/consultations.html",
        items=items,
        status=status,
        counts=counts,
        statuses=CONSULTATION_STATUSES,
    )


@bp.route("/consultations/<int:consult_id>/respond", methods=["POST"])
@verified_doctor_required
def respond_consultation(consult_id):
    consult = Consultation.query.filter_by(id=consult_id, doctor_id=current_user.id).first_or_404()
    action = request.form.get("action", "")
    if consult.status != "Pending":
        flash("This request has already been answered.", "error")
    elif action in ("accept", "decline"):
        consult.status = "Accepted" if action == "accept" else "Declined"
        consult.responded_at = datetime.now()
        db.session.commit()
        flash(f"Consultation from {consult.requester.name} {consult.status.lower()}.", "success")
    else:
        flash("Unknown action.", "error")
    return redirect(url_for("doctor.consultations"))


def doctor_child_ids():
    rows = (
        Consultation.query.with_entities(Consultation.child_id)
        .filter(
            Consultation.doctor_id == current_user.id,
            Consultation.child_id.is_not(None),
            Consultation.status.in_(["Accepted", "Closed"]),
        )
        .distinct()
        .all()
    )
    return [row.child_id for row in rows]


@bp.route("/patients")
@verified_doctor_required
def patients():
    children = Child.query.filter(Child.id.in_(doctor_child_ids())).order_by(Child.name).all()
    return render_template("doctor/patients.html", children=children)


@bp.route("/patients/<int:child_id>")
@verified_doctor_required
def patient_record(child_id):
    if child_id not in doctor_child_ids():
        abort(404)
    child = db.get_or_404(Child, child_id)
    records = child.growth_records
    latest = records[-1] if records else None
    plan_rec = Recommendation.query.filter_by(child_id=child.id).order_by(Recommendation.id.desc()).first()
    reminders = Reminder.query.filter_by(child_id=child.id).order_by(Reminder.scheduled_at.desc()).all()
    consults = (
        Consultation.query.filter_by(child_id=child.id, doctor_id=current_user.id)
        .order_by(Consultation.created_at.desc())
        .all()
    )
    return render_template(
        "doctor/patient_record.html",
        child=child,
        records=records,
        latest=latest,
        alert=growth_alert(latest),
        plan_rec=plan_rec,
        reminders=reminders,
        consults=consults,
    )