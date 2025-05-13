from app import db

class OrgConfig(db.Model):
    __tablename__ = 'org_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('org.id'), nullable=False)
    feature_type = db.Column(db.Integer, nullable=False)  # 0: 论文, 1: 课程, 2: 学生认证, 3: 学生搜索
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    def __repr__(self):
        return f'<OrgConfig {self.org_id} - {self.feature_type}>' 