from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app.models.log import Log
from app.models.user import User
from app.models.org_user import OrgUser
from app.utils.auth import login_required
from app import db

bp = Blueprint('log', __name__)

@bp.route('/logs')
@login_required
def view_logs():
    """查看日志列表"""
    # 获取查询参数
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # 根据用户角色获取日志
    if current_user.is_e_admin or current_user.is_admin:
        # 管理员可以查看所有日志
        logs = Log.query.order_by(Log.create_time.desc()).paginate(page=page, per_page=per_page)
    elif current_user.is_convener:
        # 召集人只能查看本组织用户的日志
        # 获取用户所属的组织
        org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
        if org_user:
            # 获取组织中的所有用户
            org_users = OrgUser.query.filter_by(org_id=org_user.org_id).all()
            user_ids = [ou.user_id for ou in org_users]
            logs = Log.query.filter(Log.user_id.in_(user_ids)).order_by(Log.create_time.desc()).paginate(page=page, per_page=per_page)
        else:
            # 如果用户不属于任何组织，返回空结果
            logs = Log.query.filter_by(id=None).paginate(page=page, per_page=per_page)
    else:
        return jsonify({'success': False, 'message': '没有权限查看日志'}), 403
    
    return render_template('log/logs.html', logs=logs)

def log_action(user_id, action):
    """记录用户操作日志"""
    log = Log(
        log=action,
        user_id=user_id
    )
    db.session.add(log)
    db.session.commit() 