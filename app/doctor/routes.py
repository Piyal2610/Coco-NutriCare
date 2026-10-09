from flask import Blueprint, render_template
from app.decorators import role_required
bp = Blueprint("doctor", __name__, url_prefix="/doctor")


@bp.route("/")
@role_required("doctor")
def index():
    return render_template("dashboard.html", section="Doctor")