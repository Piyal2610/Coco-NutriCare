from app.extensions import db

COMMON_ALLERGENS = ("Peanut", "Tree nuts", "Milk", "Egg", "Wheat", "Soy", "Fish", "Shellfish", "Sesame")
ALLERGY_CATEGORIES = ("Food", "Medicine")
SEVERITIES = ("Mild", "Moderate", "Severe")


class ChildAllergy(db.Model):
    __tablename__ = "child_allergies"
    __table_args__ = (
        db.CheckConstraint(f"category IN {ALLERGY_CATEGORIES}", name="ck_allergy_category"),
        db.CheckConstraint(f"severity IN {SEVERITIES}", name="ck_allergy_severity"),
        db.UniqueConstraint("child_id", "allergen", name="uq_child_allergen"),
    )

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"), nullable=False, index=True)
    allergen = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(10), nullable=False, default="Food")
    severity = db.Column(db.String(10), nullable=False, default="Mild")

    child = db.relationship(
        "Child",
        backref=db.backref("allergies", lazy=True, cascade="all, delete-orphan", order_by="ChildAllergy.allergen"),
    )

    def __repr__(self):
        return f"<ChildAllergy {self.allergen} ({self.severity})>"