from functools import wraps
from flask import abort, redirect, url_for
from flask_login import current_user, login_required


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def verified_doctor_required(view):
    @wraps(view)
    @role_required("doctor")
    def wrapped(*args, **kwargs):
        profile = current_user.doctor_profile
        if profile is None:
            return redirect(url_for("doctor.complete_profile"))
        if not profile.is_verified:
            return redirect(url_for("doctor.pending"))
        return view(*args, **kwargs)
    return wrapped