from flask import Blueprint

bp = Blueprint("maternal", __name__, url_prefix="/maternal")


@bp.route("/")
def index():
    return "Maternal section is working!"