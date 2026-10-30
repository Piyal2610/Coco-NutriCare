from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from sqlalchemy import func, or_, select
from app.extensions import db
from app.models import DoctorProfile, User, Child, GrowthRecord, Recommendation, Consultation, Reminder
from app.models.doctor_profile import VERIFICATION_STATUSES
from app.decorators import role_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

ROLE_FILTERS = ("parent", "doctor", "mother", "admin")


def plans_awaiting_review():
    latest_ids = (
        select(func.max(Recommendation.id))
        .where(Recommendation.child_id.is_not(None))
        .group_by(Recommendation.child_id)
    )
    return Recommendation.query.filter(
        Recommendation.id.in_(latest_ids),
        Recommendation.review_status == "Pending",
    ).count()


@bp.route("/")
@role_required("admin")
def index():
    stats = {
        "parents": User.query.filter_by(role="parent").count(),
        "doctors_verified": DoctorProfile.query.filter_by(verification_status="Verified").count(),
        "doctors_pending": DoctorProfile.query.filter_by(verification_status="Pending").count(),
        "mothers": User.query.filter_by(role="mother").count(),
        "children": Child.query.count(),
        "growth_records": GrowthRecord.query.count(),
        "plans_pending": plans_awaiting_review(),
        "consultations_open": Consultation.query.filter(Consultation.status.in_(["Pending", "Accepted"])).count(),
        "reminders_pending": Reminder.query.filter_by(status="Pending").count(),
        "inactive_users": User.query.filter_by(active=False).count(),
    }
    pending_doctors = (
        DoctorProfile.query.filter_by(verification_status="Pending")
        .order_by(DoctorProfile.id.desc())
        .limit(5)
        .all()
    )
    return render_template("admin/dashboard.html", stats=stats, pending_doctors=pending_doctors)


@bp.route("/users")
@role_required("admin")
def users():
    search = request.args.get("q", "").strip()
    role = request.args.get("role", "")
    query = User.query
    if role in ROLE_FILTERS:
        query = query.filter_by(role=role)
    else:
        role = ""
    if search:
        like = f"%{search}%"
        query = query.filter(or_(User.name.ilike(like), User.email.ilike(like)))
    items = query.order_by(User.role, User.name).all()
    return render_template("admin/users.html", users=items, search=search, role=role, roles=ROLE_FILTERS)


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@role_required("admin")
def toggle_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id or user.role == "admin":
        flash("Admin accounts cannot be deactivated here.", "error")
    else:
        user.active = not user.active
        db.session.commit()
        flash(f"{user.name} has been {'activated' if user.active else 'deactivated'}.", "success")
    return redirect(url_for("admin.users", q=request.form.get("q", ""), role=request.form.get("role", "")))


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