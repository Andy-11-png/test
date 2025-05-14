from app import db

class AllConfig(db.Model):
    __tablename__ = 'all_config'
    
    id = db.Column(db.Integer, primary_key=True)
    all = db.Column(db.Integer, default=0)  # 所有用户基础收费
    private = db.Column(db.Integer, default=0)  # 私有数据基础收费
    
    def __repr__(self):
        return f'<AllConfig {self.id}>' 