from datetime import date, datetime
from app.extensions import db

MATERNAL_CONDITIONS = {
    "anemia": "Anemia",
    "gestational_diabetes": "Gestational diabetes",
    "hypertension": "Hypertension / Pre-eclampsia",
    "thyroid": "Thyroid disorder",
}


class MaternalProfile(db.Model):
    __tablename__ = "maternal_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    due_date = db.Column(db.Date, nullable=False)
    conditions = db.Column(db.String(255))
    dietary_habits = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("maternal_profile", uselist=False))

    @property
    def pregnancy_week(self):
        days_pregnant = 280 - (self.due_date - date.today()).days
        return min(max(days_pregnant // 7, 0), 42)

    @property
    def trimester(self):
        week = self.pregnancy_week
        if week <= 13:
            return "First"
        if week <= 27:
            return "Second"
        return "Third"
    @property
    def condition_keys(self):
        keys = [c.strip().lower() for c in (self.conditions or "").split(",")]
        return [k for k in keys if k in MATERNAL_CONDITIONS]

    @property
    def condition_labels(self):
        return [MATERNAL_CONDITIONS[k] for k in self.condition_keys]

    @property
    def days_to_due(self):
        return (self.due_date - date.today()).days
    def __repr__(self):
        return f"<MaternalProfile user={self.user_id} week={self.pregnancy_week}>"