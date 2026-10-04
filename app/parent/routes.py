from flask import Blueprint

bp = Blueprint("parent", __name__, url_prefix="/parent")


@bp.route("/")
def index():
    return "Parent section is working!"