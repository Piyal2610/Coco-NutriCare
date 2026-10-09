from datetime import date, datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import (
    User, Child, GrowthRecord, DoctorProfile, MaternalProfile,
    Recommendation, Reminder, Consultation, Message,
)
from app.growth import update_growth_records

PASSWORD = "12345678"


def make_user(name, email, role, phone=None):
    user = User(name=name, email=email, role=role, phone=phone)
    user.set_password(PASSWORD)
    db.session.add(user)
    return user


def clear_data():
    for model in (Message, Consultation, Reminder, Recommendation, GrowthRecord,
                  Child, MaternalProfile, DoctorProfile, User):
        db.session.query(model).delete()
    db.session.commit()


def seed():
    clear_data()

    make_user("Admin", "admin@coco.com", "admin")
    parent = make_user("Amal Rahman", "parent@coco.com", "parent", "01711000001")
    mother = make_user("Nadia Rahman", "mother@coco.com", "mother", "01711000002")
    doctor = make_user("Dr. Sarah Ahmed", "doctor@coco.com", "doctor", "01711000003")
    pending_doctor = make_user("Dr. Karim Hossain", "doctor2@coco.com", "doctor", "01711000004")

    db.session.add_all([
        DoctorProfile(user=doctor, specialization="Pediatrics", license_no="BMDC-10001",
                      experience_years=8, verification_status="Verified", verified_at=datetime.utcnow()),
        DoctorProfile(user=pending_doctor, specialization="Gynecology", license_no="BMDC-10002",
                      experience_years=5),
    ])

    emma = Child(parent=parent, name="Emma Rahman", date_of_birth=date(2022, 5, 2),
                 gender="female", dietary_habits="Vegetarian-leaning")
    adam = Child(parent=parent, name="Adam Rahman", date_of_birth=date(2019, 3, 15), gender="male")
    db.session.add_all([emma, adam])

    today = date.today()
    db.session.add_all([
        GrowthRecord(child=emma, date=today - timedelta(days=60), weight_kg=12.0, height_cm=86),
        GrowthRecord(child=emma, date=today, weight_kg=12.4, height_cm=88),
        GrowthRecord(child=adam, date=today, weight_kg=24.0, height_cm=122),
    ])
    for kid in (emma, adam):
        update_growth_records(kid)

    maternal = MaternalProfile(user=mother, due_date=today + timedelta(weeks=16),
                               conditions="anemia", dietary_habits="Non-vegetarian")
    db.session.add(maternal)

    db.session.add_all([
        Recommendation(child=emma, plan_details="Breakfast: Egg, Banana, Milk. Lunch: Rice, Fish, Vegetables."),
        Recommendation(maternal=maternal, plan_details="Increase iron-rich foods: leafy greens, lentils, fortified cereals.",
                       review_status="Approved", reviewer=doctor, reviewed_at=datetime.utcnow(),
                       doctor_note="Plan is appropriate."),
    ])

    now = datetime.now()
    db.session.add_all([
        Reminder(child=emma, type="Vaccination", title="MMR - Emma", scheduled_at=now + timedelta(days=3)),
        Reminder(child=adam, type="Medicine", title="Vitamin D",
                 scheduled_at=now.replace(hour=20, minute=0, second=0, microsecond=0)),
        Reminder(maternal=maternal, type="Checkup", title="Prenatal checkup", scheduled_at=now + timedelta(days=1)),
    ])

    consultation = Consultation(requester=parent, doctor=doctor, child=emma, reason="Growth concern",
                                description="Weight gain has slowed down.", status="Accepted",
                                responded_at=datetime.utcnow())
    db.session.add(consultation)
    db.session.add_all([
        Message(consultation=consultation, sender=parent, text="My child has recently lost appetite."),
        Message(consultation=consultation, sender=doctor,
                text="I reviewed the growth chart. Please monitor her diet and schedule a follow-up."),
    ])

    db.session.commit()
    print("Demo data created. Password for all users:", PASSWORD)


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()