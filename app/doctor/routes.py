from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("doctor", __name__, url_prefix="/doctor")


@bp.route("/")
@login_required
def index():
    return render_template("dashboard.html", section="Doctor")