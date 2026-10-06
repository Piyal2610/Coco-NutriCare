from datetime import datetime
from app.extensions import db

CONSULTATION_STATUSES = ("Pending", "Accepted", "Declined", "Closed")


class Consultation(db.Model):
    __tablename__ = "consultations"
    __table_args__ = (
        db.CheckConstraint(f"status IN {CONSULTATION_STATUSES}", name="ck_consultation_status"),
        db.CheckConstraint(
            "(child_id IS NOT NULL AND maternal_id IS NULL) OR (child_id IS NULL AND maternal_id IS NOT NULL)",
            name="ck_consultation_subject",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"))
    maternal_id = db.Column(db.Integer, db.ForeignKey("maternal_profiles.id"))
    reason = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(10), nullable=False, default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)

    requester = db.relationship("User", foreign_keys=[requester_id], backref=db.backref("consultations_requested", lazy=True))
    doctor = db.relationship("User", foreign_keys=[doctor_id], backref=db.backref("consultations_received", lazy=True))
    child = db.relationship("Child", backref=db.backref("consultations", lazy=True, cascade="all, delete-orphan"))
    maternal = db.relationship("MaternalProfile", backref=db.backref("consultations", lazy=True))
    messages = db.relationship(
        "Message",
        backref="consultation",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Message.sent_at",
    )

    def __repr__(self):
        return f"<Consultation {self.id} {self.reason} ({self.status})>"