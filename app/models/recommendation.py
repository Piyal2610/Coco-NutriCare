from datetime import datetime
from app.extensions import db

REVIEW_STATUSES = ("Pending", "Approved", "Flagged")


class Recommendation(db.Model):
    _tablename_ = "recommendations"
    _table_args_ = (
        db.CheckConstraint(f"review_status IN {REVIEW_STATUSES}", name="ck_recommendation_review_status"),
        db.CheckConstraint(
            "(child_id IS NOT NULL AND maternal_id IS NULL) OR (child_id IS NULL AND maternal_id IS NOT NULL)",
            name="ck_recommendation_owner",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"), index=True)
    maternal_id = db.Column(db.Integer, db.ForeignKey("maternal_profiles.id"), index=True)
    plan_details = db.Column(db.Text, nullable=False)
    review_status = db.Column(db.String(10), nullable=False, default="Pending")
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.DateTime)
    doctor_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    child = db.relationship("Child", backref=db.backref("recommendations", lazy=True))
    maternal = db.relationship("MaternalProfile", backref=db.backref("recommendations", lazy=True))
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def _repr_(self):
        return f"<Recommendation {self.id} ({self.review_status})>"