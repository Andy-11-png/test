from app import db
from datetime import datetime, timedelta

class EmailVerify(db.Model):
    __tablename__ = 'email_verify'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_used = db.Column(db.Boolean, default=False)
    
    def is_expired(self):
        """检查验证码是否过期（5分钟内有效）"""
        return datetime.utcnow() > self.created_at + timedelta(minutes=5)
    
    def mark_as_used(self):
        """标记验证码为已使用"""
        self.is_used = True
        db.session.commit() 