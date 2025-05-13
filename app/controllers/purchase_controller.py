from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.purchase import Purchase
from app.models.user import User
from app import db
from datetime import datetime

bp = Blueprint('purchase', __name__)

@bp.route('/purchases')
@login_required
def list_purchases():
    """显示用户的购买记录"""
    purchases = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.purchase_time.desc()).all()
    return render_template('purchase/list.html', purchases=purchases)

@bp.route('/purchase/create', methods=['POST'])
@login_required
def create_purchase():
    """创建新的购买记录"""
    try:
        content_id = request.form.get('content_id')
        content_type = request.form.get('content_type')
        price = request.form.get('price', type=int)
        
        if not all([content_id, content_type, price]):
            flash('缺少必要的购买信息', 'error')
            return redirect(request.referrer or url_for('main.index'))
            
        # 检查用户积分是否足够
        if current_user.points < price:
            flash('积分不足，无法完成购买', 'error')
            return redirect(request.referrer or url_for('main.index'))
            
        # 创建购买记录
        purchase = Purchase(
            user_id=current_user.id,
            content_id=content_id,
            content_type=content_type,
            price=price,
            purchase_time=datetime.now()
        )
        
        # 扣除用户积分
        current_user.points -= price
        
        db.session.add(purchase)
        db.session.commit()
        
        flash('购买成功！', 'success')
        return redirect(url_for('purchase.list_purchases'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'购买失败：{str(e)}', 'error')
        return redirect(request.referrer or url_for('main.index')) 