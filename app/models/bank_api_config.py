from app import db
from datetime import datetime

class BankApiConfig(db.Model):
    __tablename__ = 'bank_api_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    feature_type = db.Column(db.Integer, nullable=False)  # 1 for authenticate, 2 for transfer
    api_url = db.Column(db.String(255), nullable=False)
    api_path = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    input_schema = db.Column(db.Text, nullable=False)
    output_schema = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<BankApiConfig {self.feature_type}>' 