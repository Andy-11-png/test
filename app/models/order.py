from app import db

class UserOrder(db.Model):
    __tablename__ = 'user_order'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    order_id = db.Column(db.Integer)  # 关联的内容ID（课程/论文/学生ID）
    order_type = db.Column(db.Integer)  # 0:学生, 1:课程, 2:论文
    user = db.relationship('User', backref='orders') 