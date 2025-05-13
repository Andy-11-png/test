from app import db
from datetime import datetime

class UserOrder(db.Model):
    __tablename__ = 'user_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('org.id'), nullable=False)  # 服务提供组织
    service_id = db.Column(db.Integer, db.ForeignKey('org_config.id'), nullable=False)  # 使用的服务
    amount = db.Column(db.Float, nullable=False)  # 交易金额
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    user = db.relationship('User', backref='orders')
    org = db.relationship('Org', backref='service_orders')
    service = db.relationship('OrgConfig', backref='orders')
    
    def __repr__(self):
        return f'<UserOrder {self.id}>' 