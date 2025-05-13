from app import db
from datetime import datetime

class Log(db.Model):
    __tablename__ = 'log'
    
    id = db.Column(db.Integer, primary_key=True)
    log = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    create_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 添加与 User 模型的关联
    user = db.relationship('User', backref='logs')
    
    def __repr__(self):
        return f'<Log {self.id}: {self.log}>' 