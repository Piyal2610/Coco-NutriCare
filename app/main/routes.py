from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Consultation, Message

bp = Blueprint("main", __name__)

MAX_MESSAGE_LENGTH = 2000


@bp.route("/")
def index():
    return render_template("main/index.html")


def get_my_consultation(consult_id):
    consult = db.get_or_404(Consultation, consult_id)
    if current_user.id not in (consult.requester_id, consult.doctor_id):
        abort(404)
    return consult


def consultations_page_for(user, consult):
    if user.id == consult.doctor_id:
        return url_for("doctor.consultations", status=consult.status)
    if user.role == "parent":
        return url_for("parent.consultations")
    return url_for("maternal.index")


@bp.route("/consultations/<int:consult_id>/messages", methods=["GET", "POST"])
@login_required
def consultation_messages(consult_id):
    consult = get_my_consultation(consult_id)
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if consult.status != "Accepted":
            flash("Messages can only be sent while the consultation is accepted.", "error")
        elif not text:
            flash("Message cannot be empty.", "error")
        elif len(text) > MAX_MESSAGE_LENGTH:
            flash(f"Message is too long (max {MAX_MESSAGE_LENGTH} characters).", "error")
        else:
            db.session.add(Message(consultation=consult, sender_id=current_user.id, text=text, sent_at=datetime.now()))
            db.session.commit()
        return redirect(url_for("main.consultation_messages", consult_id=consult.id))
    other = consult.doctor if current_user.id == consult.requester_id else consult.requester
    return render_template(
        "consultation_messages.html",
        consult=consult,
        other=other,
        back=consultations_page_for(current_user, consult),
    )


@bp.route("/consultations/<int:consult_id>/close", methods=["POST"])
@login_required
def close_consultation(consult_id):
    consult = get_my_consultation(consult_id)
    if consult.status == "Accepted":
        consult.status = "Closed"
        db.session.commit()
        flash("Consultation closed.", "success")
    else:
        flash("Only an accepted consultation can be closed.", "error")
    return redirect(url_for("main.consultation_messages", consult_id=consult.id))