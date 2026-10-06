from datetime import date, datetime
from app.extensions import db

GENDERS = ("male", "female")


class Child(db.Model):
    __tablename__ = "children"
    __table_args__ = (db.CheckConstraint(f"gender IN {GENDERS}", name="ck_child_gender"),)

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    dietary_habits = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship("User", backref=db.backref("children", lazy=True))
    growth_records = db.relationship(
        "GrowthRecord",
        backref="child",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="GrowthRecord.date",
    )

    @property
    def age_months(self):
        today = date.today()
        months = (today.year - self.date_of_birth.year) * 12 + (today.month - self.date_of_birth.month)
        if today.day < self.date_of_birth.day:
            months -= 1
        return max(months, 0)

    @property
    def age_display(self):
        years, months = divmod(self.age_months, 12)
        if years == 0:
            return f"{months}m"
        return f"{years}y {months}m"

    def __repr__(self):
        return f"<Child {self.name}>"