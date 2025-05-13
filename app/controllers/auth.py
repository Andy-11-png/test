from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.utils.email_utils import send_verification_email, verify_email_code
from app import db
from app.controllers.log_controller import log_action
import logging
from app.models import OrgUser

logger = logging.getLogger(__name__)
bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        verification_code = request.form.get('verification_code')
        
        logger.debug(f"Login attempt - Email: {email}, Verification code: {verification_code}")
        
        if not all([email, password, verification_code]):
            flash('请填写完整信息', 'error')
            return redirect(url_for('auth.login'))
        
        # 验证邮箱验证码
        if not verify_email_code(email, verification_code):
            logger.debug(f"Verification code failed for email: {email}")
            flash('验证码错误或已过期', 'error')
            return redirect(url_for('auth.login'))
        
        # 验证用户
        user = User.query.filter_by(email=email).first()
        logger.debug(f"User found: {user is not None}")
        
        if user:
            logger.debug(f"User status: {user.status}")
            password_check = user.check_password(password)
            logger.debug(f"Password check result: {password_check}")
            
            if password_check:
                if user.status not in ['1', '2']:  # 检查用户状态
                    logger.debug(f"User status not approved: {user.status}")
                    flash('账号未审批或已被拒绝', 'error')
                    return redirect(url_for('auth.login'))
                
                login_user(user)
                log_action(user.id, f'用户登录成功')
                org = OrgUser.query.filter_by(user_id=user.id).first()

                if user.is_admin or user.is_convener:
                    return redirect(url_for('main.index'))
                else:
                    return redirect(url_for('main.org_services', org_id=org.org_id))
        
        logger.debug("Login failed - Invalid email or password")
        flash('邮箱或密码错误', 'error')
    
    return render_template('login.html')

@bp.route('/send_code', methods=['POST'])
def send_code():
    email = request.json.get('email')
    if not email:
        return jsonify({'success': False, 'message': '邮箱不能为空'})
    
    if send_verification_email(email):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '发送验证码失败'})

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index')) 