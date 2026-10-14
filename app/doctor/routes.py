import re
from sqlalchemy import func, select
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from app.extensions import db
from app.models import DoctorProfile, Recommendation
from app.models.recommendation import REVIEW_STATUSES
from app.nutrition import cross_check
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
        db.session.commit()
        flash(f"Plan for {rec.child.name} marked as {rec.review_status}.", "success")
    return redirect(url_for("doctor.reviews"))