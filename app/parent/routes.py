from datetime import date, datetime, timedelta
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Child, GrowthRecord, Reminder, Consultation, ChildAllergy, Recommendation, User, DoctorProfile
from app.models.child import GENDERS, ALLERGY_STATUSES
from app.models.reminder import REMINDER_TYPES
from app.models.allergy import COMMON_ALLERGENS, ALLERGY_CATEGORIES, SEVERITIES, REACTION_SYMPTOMS
from app.models.consultation import CONSULTATION_REASONS
from app.growth import weight_percentile, growth_trend, update_growth_records, weight_at_z, growth_alert
from app.nutrition import create_recommendation, cross_check
from app.report import build_child_report
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
    plan_rec = Recommendation.query.filter_by(child_id=child.id).order_by(Recommendation.id.desc()).first()
    return render_template("parent/child_form.html", child=None , plan_rec=plan_rec)


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

    selected_type = request.args.get("type", "All")
    query = Reminder.query.join(Child).filter(Child.parent_id == current_user.id)
    if selected_type in REMINDER_TYPES:
        query = query.filter(Reminder.type == selected_type)
    else:
        selected_type = "All"
    items = query.order_by(Reminder.scheduled_at).all()
    return render_template(
        "parent/reminders.html",
        reminders=items,
        types=REMINDER_TYPES,
        selected_type=selected_type,
        today=date.today(),
    )


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


@bp.route("/children/<int:child_id>/allergies", methods=["GET", "POST"])
@role_required("parent")
def child_allergies(child_id):
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    if request.method == "POST":
        existing = {a.allergen: a for a in child.allergies}
        for allergen in COMMON_ALLERGENS:
            checked = request.form.get(f"allergen_{allergen}") == "on"
            severity = request.form.get(f"severity_{allergen}", "Mild")
            if severity not in SEVERITIES:
                severity = "Mild"
            if checked and allergen in existing:
                existing[allergen].severity = severity
            elif checked:
                db.session.add(ChildAllergy(child=child, allergen=allergen, category="Food", severity=severity))
            elif allergen in existing:
                db.session.delete(existing[allergen])
        if any(request.form.get(f"allergen_{a}") == "on" for a in COMMON_ALLERGENS):
            child.allergy_status = "known"
        db.session.commit()
        flash("Allergy checklist saved.", "success")
        return redirect(url_for("parent.child_allergies", child_id=child.id))
    existing = {a.allergen: a for a in child.allergies}
    others = [a for a in child.allergies if a.allergen not in COMMON_ALLERGENS]
    return render_template(
        "parent/allergies.html",
        child=child,
        common=COMMON_ALLERGENS,
        existing=existing,
        others=others,
        categories=ALLERGY_CATEGORIES,
        severities=SEVERITIES,
    )


@bp.route("/children/<int:child_id>/allergies/add", methods=["POST"])
@role_required("parent")
def add_other_allergy(child_id):
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    allergen = request.form.get("allergen", "").strip().capitalize()
    category = request.form.get("category", "")
    severity = request.form.get("severity", "")
    if not allergen:
        flash("Please enter an allergen name.", "error")
    elif category not in ALLERGY_CATEGORIES or severity not in SEVERITIES:
        flash("Please choose a valid type and severity.", "error")
    elif any(a.allergen.lower() == allergen.lower() for a in child.allergies):
        flash(f"{allergen} is already in the list.", "error")
    else:
        db.session.add(ChildAllergy(child=child, allergen=allergen, category=category, severity=severity))
        child.allergy_status = "known"
        db.session.commit()
        flash(f"{allergen} added.", "success")
    return redirect(url_for("parent.child_allergies", child_id=child.id))


@bp.route("/allergies/<int:allergy_id>/delete", methods=["POST"])
@role_required("parent")
def delete_allergy(allergy_id):
    allergy = (
        ChildAllergy.query.join(Child)
        .filter(ChildAllergy.id == allergy_id, Child.parent_id == current_user.id)
        .first_or_404()
    )
    child_id = allergy.child_id
    name = allergy.allergen
    db.session.delete(allergy)
    db.session.commit()
    flash(f"{name} removed.", "success")
    return redirect(url_for("parent.child_allergies", child_id=child_id))


@bp.route("/children/<int:child_id>/allergies/status", methods=["POST"])
@role_required("parent")
def set_allergy_status(child_id):
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    status = request.form.get("allergy_status", "")
    if status not in ALLERGY_STATUSES:
        flash("Please choose an option.", "error")
        return redirect(url_for("parent.child_allergies", child_id=child.id))
    if status == "none":
        for allergy in list(child.allergies):
            db.session.delete(allergy)
        flash(f"Saved: {child.name} has no known allergies.", "success")
    elif status == "known":
        flash("Saved. Please tick the allergies below.", "success")
    child.allergy_status = status
    db.session.commit()
    if status == "not_sure":
        return redirect(url_for("parent.allergy_assessment", child_id=child.id))
    return redirect(url_for("parent.child_allergies", child_id=child.id))


@bp.route("/children/<int:child_id>/allergies/assess", methods=["GET", "POST"])
@role_required("parent")
def allergy_assessment(child_id):
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    if request.method == "POST":
        foods = [f for f in request.form.getlist("foods") if f in COMMON_ALLERGENS]
        symptoms = [s for s in request.form.getlist("symptoms") if s in REACTION_SYMPTOMS]
        timing = request.form.get("timing", "")
        if not foods:
            flash("Please choose at least one food.", "error")
        elif not symptoms:
            flash("Please choose at least one reaction.", "error")
        else:
            severity = max((REACTION_SYMPTOMS[s][1] for s in symptoms), key=SEVERITIES.index)
            existing = {a.allergen: a for a in child.allergies}
            for food in foods:
                if food in existing:
                    if SEVERITIES.index(severity) > SEVERITIES.index(existing[food].severity):
                        existing[food].severity = severity
                else:
                    db.session.add(ChildAllergy(child=child, allergen=food, category="Food", severity=severity, suspected=True))
            db.session.commit()
            return render_template(
                "parent/allergy_result.html",
                child=child,
                foods=foods,
                severity=severity,
                urgent="breathing" in symptoms or "swelling" in symptoms,
                quick=timing == "within_2h",
            )
    return render_template(
        "parent/allergy_assessment.html",
        child=child,
        common=COMMON_ALLERGENS,
        symptoms=REACTION_SYMPTOMS,
    )


@bp.route("/children/<int:child_id>/nutrition")
@role_required("parent")
def nutrition_plan(child_id):
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    recommendation = (
        Recommendation.query.filter_by(child_id=child.id)
        .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
        .first()
    )
    plan = recommendation.plan if recommendation else None
    conflicts = cross_check(plan, child) if plan else []
    return render_template(
        "parent/nutrition.html",
        child=child,
        recommendation=recommendation,
        plan=plan,
        conflicts=conflicts,
    )


@bp.route("/children/<int:child_id>/nutrition/regenerate", methods=["POST"])
@role_required("parent")
def regenerate_plan(child_id):
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    try:
        create_recommendation(child)
        flash("A new nutrition plan has been generated.", "success")
    except ValueError:
        flash("Could not create a safe plan. Please check the allergy list.", "error")
    return redirect(url_for("parent.nutrition_plan", child_id=child.id))


def verified_doctors():
    return (
        User.query.join(DoctorProfile, DoctorProfile.user_id == User.id)
        .filter(User.role == "doctor", DoctorProfile.verification_status == "Verified")
        .order_by(User.name)
        .all()
    )


@bp.route("/children/<int:child_id>/consult", methods=["GET", "POST"])
@role_required("parent")
def request_consultation(child_id):
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
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
            Consultation.child_id == child.id,
            Consultation.doctor_id == doctor.id,
            Consultation.status.in_(["Pending", "Accepted"]),
        ).first():
            flash(f"You already have an open consultation with {doctor.name} for {child.name}.", "error")
        else:
            db.session.add(Consultation(
                requester_id=current_user.id,
                doctor_id=doctor.id,
                child_id=child.id,
                reason=reason,
                created_at=datetime.now(),
                description=description or None,
            ))
            db.session.commit()
            flash(f"Consultation request sent to {doctor.name}.", "success")
            return redirect(url_for("parent.consultations"))
    return render_template("parent/consult_form.html", child=child, doctors=doctors, reasons=CONSULTATION_REASONS)


@bp.route("/consultations")
@role_required("parent")
def consultations():
    items = (
        Consultation.query.filter_by(requester_id=current_user.id)
        .order_by(Consultation.created_at.desc())
        .all()
    )
    return render_template("parent/consultations.html", consultations=items)


@bp.route("/children/<int:child_id>/report.pdf")
@role_required("parent")
def child_report(child_id):
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    pdf = build_child_report(child)
    filename = f"{child.name.replace(' ', '_')}_CocoNutriCare_Report.pdf"
    return send_file(BytesIO(pdf), mimetype="application/pdf", as_attachment=True, download_name=filename)