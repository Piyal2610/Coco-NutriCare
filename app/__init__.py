from flask import Flask
from config import Config
from .extensions import db, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)

    from .main.routes import bp as main_bp
    from .auth.routes import bp as auth_bp
    from .parent.routes import bp as parent_bp
    from .doctor.routes import bp as doctor_bp
    from .maternal.routes import bp as maternal_bp
    from .admin.routes import bp as admin_bp

    for bp in (main_bp, auth_bp, parent_bp, doctor_bp, maternal_bp, admin_bp):
        app.register_blueprint(bp)

    return app