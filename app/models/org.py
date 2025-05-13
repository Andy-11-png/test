from app import db
from datetime import datetime

class Org(db.Model):
    __tablename__ = 'org'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    short_name = db.Column(db.String(50))  # 组织简称
    bank_name = db.Column(db.String(100))  # 银行名称
    bank_account = db.Column(db.String(50))  # 银行账号
    bank_password = db.Column(db.String(100))  # 银行密码
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 组织所有者ID
    
    # 添加与 OrgUser 的关系
    users = db.relationship('OrgUser', backref='org', lazy='dynamic')
    configs = db.relationship('OrgConfig', backref='org', lazy='dynamic')
    owner = db.relationship('User', backref='owned_orgs')  # 与所有者的关系
    
    def __repr__(self):
        return f'<Org {self.name}>' 