from flask import Blueprint

bp = Blueprint("doctor", __name__, url_prefix="/doctor")


@bp.route("/")
def index():
    return "Doctor section is working!"