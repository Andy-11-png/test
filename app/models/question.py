from app import db
from datetime import datetime

class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)  # 问题标题
    description = db.Column(db.Text, nullable=False)  # 问题描述
    asker_email = db.Column(db.String(255), nullable=False)  # 提问者邮箱
    asker_role = db.Column(db.String(255), nullable=False)  # 提问者角色
    submit_time = db.Column(db.DateTime, default=datetime.now)  # 提交时间
    status = db.Column(db.String(20), default='pending')  # 状态：pending, answered
    answer = db.Column(db.Text)  # 回答内容
    answer_time = db.Column(db.DateTime)  # 回答时间
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 回答的管理员ID
    admin = db.relationship('User', backref='answered_questions')  # 与管理员的关系

    def __repr__(self):
        return f'<Question {self.title}>' 