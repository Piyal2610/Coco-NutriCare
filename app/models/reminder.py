from datetime import datetime
from app.extensions import db

REMINDER_TYPES = ("Vaccination", "Medicine", "Checkup", "Nutrition", "Other")
REMINDER_STATUSES = ("Pending", "Completed", "Snoozed", "Missed")


class Reminder(db.Model):
    __tablename__ = "reminders"
    __table_args__ = (
        db.CheckConstraint(f"type IN {REMINDER_TYPES}", name="ck_reminder_type"),
        db.CheckConstraint(f"status IN {REMINDER_STATUSES}", name="ck_reminder_status"),
        db.CheckConstraint(
            "(child_id IS NOT NULL AND maternal_id IS NULL) OR (child_id IS NULL AND maternal_id IS NOT NULL)",
            name="ck_reminder_owner",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"), index=True)
    maternal_id = db.Column(db.Integer, db.ForeignKey("maternal_profiles.id"), index=True)
    type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(10), nullable=False, default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    child = db.relationship("Child", backref=db.backref("reminders", lazy=True))
    maternal = db.relationship("MaternalProfile", backref=db.backref("reminders", lazy=True))

    @property
    def is_overdue(self):
        return self.status == "Pending" and self.scheduled_at < datetime.now()

    def __repr__(self):
        return f"<Reminder {self.title} ({self.status})>"