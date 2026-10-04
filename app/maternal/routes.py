from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("maternal", __name__, url_prefix="/maternal")


@bp.route("/")
@login_required
def index():
    return render_template("dashboard.html", section="Maternal")