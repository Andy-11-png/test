from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
import logging

# 配置日志
logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            logger.warning("未登录用户尝试访问受保护的路由")
            flash('请先登录', 'warning')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def check_permission(required_active=None, required_role=None):
    """
    权限检查装饰器
    
    Args:
        required_active: 需要的 active 等级，None 表示不检查
        required_role: 需要的角色，None 表示不检查
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                logger.warning("未登录用户尝试访问受保护的路由")
                flash('请先登录', 'warning')
                return redirect(url_for('main.login'))
            
            if current_user.status != '1':
                logger.warning(f"用户 {current_user.email} 尝试访问但账号未激活")
                flash('账号未激活', 'warning')
                return redirect(url_for('main.login'))
            
            # 检查 active 权限
            if required_active is not None:
                user_actives = current_user.actives
                active_levels = [ua.active.lv for ua in user_actives]
                if not any(lv >= required_active for lv in active_levels):
                    logger.warning(f"用户 {current_user.email} 尝试访问需要 active 等级 {required_active} 的路由，当前最高等级为 {max(active_levels) if active_levels else 0}")
                    flash('权限不足：需要更高的 active 等级', 'warning')
                    return redirect(url_for('main.index'))
            
            # 检查 role 权限
            if required_role is not None:
                if not any(ur.role.value == required_role for ur in current_user.user_roles):
                    logger.warning(f"用户 {current_user.email} 尝试访问需要角色 {required_role} 的路由")
                    flash('权限不足：需要特定角色', 'warning')
                    return redirect(url_for('main.index'))
            
            logger.debug(f"用户 {current_user.email} 成功通过权限检查，访问 {f.__name__}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator 