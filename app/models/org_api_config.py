from app import db
from datetime import datetime

class OrgApiConfig(db.Model):
    __tablename__ = 'org_api_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('org.id'), nullable=False)
    feature_type = db.Column(db.Integer, nullable=False)  # 0: 学生认证, 1: 学生查询, 2: 论文搜索, 3: 论文PDF
    api_url = db.Column(db.String(255), nullable=False)
    api_path = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    input_schema = db.Column(db.Text, nullable=False)  # JSON schema
    output_schema = db.Column(db.Text, nullable=False)  # JSON schema
    service_price = db.Column(db.Integer, nullable=True)  # 服务价格
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联关系
    org = db.relationship('Org', backref=db.backref('api_configs', lazy=True))
    
    FEATURE_TYPES = {
        0: "学生认证",
        1: "学生查询",
        2: "论文搜索",
        3: "论文PDF获取"
    }
    
    def to_dict(self):
        return {
            'id': self.id,
            'org_id': self.org_id,
            'feature_type': self.feature_type,
            'api_url': self.api_url,
            'api_path': self.api_path,
            'method': self.method,
            'input_schema': self.input_schema,
            'output_schema': self.output_schema,
            'service_price': self.service_price,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<OrgApiConfig {self.org_id}-{self.feature_type}>' 