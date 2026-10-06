import datetime
from app.extensions import db


class GrowthRecord(db.Model):
    __tablename__ = "growth_records"

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=datetime.date.today)
    weight_kg = db.Column(db.Float, nullable=False)
    height_cm = db.Column(db.Float, nullable=False)
    percentile = db.Column(db.Float)
    trend = db.Column(db.String(20))

    def __repr__(self):
        return f"<GrowthRecord child={self.child_id} {self.date} {self.weight_kg}kg>"