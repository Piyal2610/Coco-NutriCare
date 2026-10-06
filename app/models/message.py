from datetime import datetime
from app.extensions import db


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(db.Integer, db.ForeignKey("consultations.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sender = db.relationship("User")

    def __repr__(self):
        return f"<Message {self.id} from user={self.sender_id}>"