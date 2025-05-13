from app import db

class OrgUser(db.Model):
    __tablename__ = 'org_user'
    
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('org.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<OrgUser {self.id}: org_id={self.org_id}, user_id={self.user_id}>' 