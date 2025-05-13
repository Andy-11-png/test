from app import db
from datetime import datetime

class Purchase(db.Model):
    __tablename__ = 'purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_id = db.Column(db.Integer, nullable=False)
    content_type = db.Column(db.String(20), nullable=False)  # 'paper' or 'course'
    price = db.Column(db.Integer, nullable=False)
    purchase_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    def __repr__(self):
        return f'<Purchase {self.id} by user {self.user_id}>' 