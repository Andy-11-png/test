from app import db
from datetime import datetime

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    describe = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='courses')

class Paper(db.Model):
    __tablename__ = 'paper'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    describe = db.Column(db.Text)
    price = db.Column(db.Integer, default=0)  # 论文价格
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='papers')

class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    in_year = db.Column(db.String(255))
    out_year = db.Column(db.String(255))
    gpa = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.String(255))  # 注意这里是String类型，与表结构保持一致 