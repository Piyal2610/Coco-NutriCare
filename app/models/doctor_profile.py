from datetime import datetime
from app.extensions import db

VERIFICATION_STATUSES = ("Pending", "Verified", "Rejected")


class DoctorProfile(db.Model):
    __tablename__ = "doctor_profiles"
    __table_args__ = (
        db.CheckConstraint(f"verification_status IN {VERIFICATION_STATUSES}", name="ck_doctor_verification_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    specialization = db.Column(db.String(120), nullable=False)
    license_no = db.Column(db.String(50), nullable=False, unique=True)
    experience_years = db.Column(db.Integer, nullable=False, default=0)
    verification_status = db.Column(db.String(10), nullable=False, default="Pending")
    rejection_reason = db.Column(db.String(255))
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("doctor_profile", uselist=False))

    @property
    def is_verified(self):
        return self.verification_status == "Verified"

    def __repr__(self):
        return f"<DoctorProfile {self.license_no} ({self.verification_status})>"