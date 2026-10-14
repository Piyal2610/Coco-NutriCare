from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import DoctorProfile
from app.models.doctor_profile import VERIFICATION_STATUSES
from app.decorators import role_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@role_required("admin")
def index():
    return render_template("dashboard.html", section="Admin")


@bp.route("/doctors")
@role_required("admin")
def doctors():
    status = request.args.get("status", "Pending")
    if status not in VERIFICATION_STATUSES:
        status = "Pending"
    profiles = DoctorProfile.query.filter_by(verification_status=status).order_by(DoctorProfile.id).all()
    counts = {s: DoctorProfile.query.filter_by(verification_status=s).count() for s in VERIFICATION_STATUSES}
    return render_template(
        "admin/doctors.html",
        profiles=profiles,
        status=status,
        counts=counts,
        statuses=VERIFICATION_STATUSES,
    )


@bp.route("/doctors/<int:profile_id>/verify", methods=["POST"])
@role_required("admin")
def verify_doctor(profile_id):
    profile = db.get_or_404(DoctorProfile, profile_id)
    old_status = profile.verification_status
    action = request.form.get("action", "")
    if action == "approve":
        profile.verification_status = "Verified"
        profile.verified_at = datetime.now()
        profile.rejection_reason = None
        flash(f"{profile.user.name} has been verified.", "success")
    elif action == "reject":
        reason = request.form.get("reason", "").strip()
        if not reason:
            flash("Please give a reason for rejection.", "error")
            return redirect(url_for("admin.doctors", status=old_status))
        profile.verification_status = "Rejected"
        profile.verified_at = None
        profile.rejection_reason = reason
        flash(f"{profile.user.name} has been rejected.", "success")
    else:
        flash("Unknown action.", "error")
        return redirect(url_for("admin.doctors", status=old_status))
    db.session.commit()
    return redirect(url_for("admin.doctors", status=old_status))