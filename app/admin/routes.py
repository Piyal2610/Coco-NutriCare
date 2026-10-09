from flask import Blueprint, render_template
from app.decorators import role_required
bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@role_required("admin")
def index():
    return render_template("dashboard.html", section="Admin")