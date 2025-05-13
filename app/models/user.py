from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
import logging
from .org_user import OrgUser
from .org_config import OrgConfig

logger = logging.getLogger(__name__)

class UserRole(db.Model):
    __tablename__ = 'user_role'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    user = db.relationship('User', backref=db.backref('user_roles', lazy='dynamic'))
    role = db.relationship('Role', backref=db.backref('user_roles', lazy='dynamic'))

class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    value = db.Column(db.String(255))

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(255), default='0')  # 0: 待审批, 1: e-admin已审批, 2: he-admin已审批, 3: 已拒绝
    e_admin_approver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    he_admin_approver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 修改关系定义，添加 remote_side
    e_admin_approver = db.relationship('User', 
                                     foreign_keys=[e_admin_approver_id],
                                     remote_side=[id],
                                     backref=db.backref('e_approved_users', lazy='dynamic'))
    
    he_admin_approver = db.relationship('User',
                                      foreign_keys=[he_admin_approver_id],
                                      remote_side=[id],
                                      backref=db.backref('he_approved_users', lazy='dynamic'))
    
    actives = db.relationship('UserActive', backref=db.backref('user', lazy=True), lazy='dynamic')
    org_users = db.relationship('OrgUser', backref='user', lazy=True)

    def set_password(self, password):
        logger.debug(f"Setting password for user {self.email}")
        self.password = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        logger.debug(f"Checking password for user {self.email}")
        result = check_password_hash(self.password, password)
        logger.debug(f"Password check result: {result}")
        return result

    @property
    def is_admin(self):
        return any(ur.role.value == 'admin' for ur in self.user_roles)

    @property
    def is_e_admin(self):
        return any(ur.role.value == 'e-admin' for ur in self.user_roles)

    @property
    def is_he_admin(self):
        return any(ur.role.value == 'he-admin' for ur in self.user_roles)

    @property
    def is_convener(self):
        return any(ur.role.value == 'convener' for ur in self.user_roles)

    @property
    def is_default(self):
        return any(ur.role.value == 'default' for ur in self.user_roles)

    def __repr__(self):
        return f'<User {self.name}>'

    def has_role(self, role_value):
        return any(ur.role.value == role_value for ur in self.user_roles)

    def is_active(self):
        # 检查用户是否有任何激活的 active 记录
        return any(ua.active.lv > 0 for ua in self.actives.all())

    @property
    def quota(self):
        # 获取用户余额
        if hasattr(self, 'account') and self.account:
            return self.account.quota
        return 0

    def has_permission_level(self, required_level):
        """
        检查用户是否有指定等级或更高的权限
        Args:
            required_level: 需要的权限等级
        Returns:
            bool: 如果用户有足够权限返回True，否则返回False
        """
        actives = self.actives.all()
        if not actives:
            return False
        # 获取用户最高的权限等级
        max_level = max(ua.active.lv for ua in actives)
        return max_level >= required_level

    @property
    def org_configs(self):
        if not hasattr(self, '_org_configs'):
            org_user = OrgUser.query.filter_by(user_id=self.id).first()
            if org_user:
                self._org_configs = OrgConfig.query.filter_by(org_id=org_user.org_id).all()
            else:
                self._org_configs = []
        return self._org_configs

class Active(db.Model):
    __tablename__ = 'active'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    lv = db.Column(db.Integer)

class UserActive(db.Model):
    __tablename__ = 'user_active'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    active_id = db.Column(db.Integer, db.ForeignKey('active.id'))
    active = db.relationship('Active', backref='user_actives', lazy=True)

class UserAccount(db.Model):
    __tablename__ = 'user_account'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    quota = db.Column(db.Integer, default=0)
    user = db.relationship('User', backref='account') 