from flask import Blueprint, render_template
from app.decorators import role_required

bp = Blueprint("maternal", __name__, url_prefix="/maternal")


@bp.route("/")
@role_required("mother")
def index():
    return render_template("dashboard.html", section="Maternal")