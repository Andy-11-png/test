from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Question, User
from app.utils.auth import login_required, check_permission
from app import db
from datetime import datetime
from flask_login import current_user

bp = Blueprint('question', __name__)

@bp.route('/questions')
@login_required
def question_list():
    # 获取所有问题，按时间倒序排列
    questions = Question.query.order_by(Question.submit_time.desc()).all()
    return render_template('question/list.html', questions=questions)

@bp.route('/questions/ask', methods=['GET', 'POST'])
@login_required
def ask_question():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        if not all([title, description]):
            flash('请填写所有必填字段')
            return redirect(url_for('question.ask_question'))
        
        question = Question(
            title=title,
            description=description,
            asker_email=current_user.email,
            asker_role=next((ur.role.name for ur in current_user.user_roles), '默认'),
            submit_time=datetime.now(),
            status='待回答'
        )
        
        try:
            db.session.add(question)
            db.session.commit()
            flash('问题提交成功')
            return redirect(url_for('question.question_list'))
        except Exception as e:
            db.session.rollback()
            flash('提交失败，请重试')
            return redirect(url_for('question.ask_question'))
    
    return render_template('question/ask.html')

@bp.route('/questions/<int:question_id>')
@login_required
def view_question(question_id):
    question = Question.query.get_or_404(question_id)
    return render_template('question/view.html', question=question)

@bp.route('/questions/<int:question_id>/answer', methods=['POST'])
@login_required
def answer_question(question_id):
    if not current_user.is_admin:
        flash('只有管理员可以回答问题', 'error')
        return redirect(url_for('question.view_question', question_id=question_id))
        
    question = Question.query.get_or_404(question_id)
    
    # 检查问题是否已经被回答
    if question.status == 'answered':
        flash('该问题已经被回答', 'error')
        return redirect(url_for('question.view_question', question_id=question_id))
    
    answer = request.form.get('answer', '').strip()
    if not answer:
        flash('请填写回答内容', 'error')
        return redirect(url_for('question.view_question', question_id=question_id))
    
    try:
        question.answer = answer
        question.status = 'answered'
        question.answer_time = datetime.now()
        question.admin_id = current_user.id
        
        db.session.commit()
        flash('回答提交成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash('提交失败，请重试', 'error')
    
    return redirect(url_for('question.view_question', question_id=question_id))

@bp.route('/questions/pending')
@login_required
def pending_questions():
    if not current_user.is_admin:
        flash('只有管理员可以查看待回答问题')
        return redirect(url_for('question.question_list'))
        
    questions = Question.query.filter_by(status='pending').order_by(Question.submit_time.asc()).all()
    return render_template('question/pending.html', questions=questions) 