from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app import db
from app.models.academic import Course, Paper, Student
from app.models.org import Org
from app.models.user import Active, UserActive, User, UserAccount
from app.models.order import UserOrder
from app.models.purchase import Purchase
from app.models.org_user import OrgUser
from app.models.question import Question
from app.models.org_config import OrgConfig
from app.models.org_api_config import OrgApiConfig
from app.utils.api_utils import get_org_api_config, generate_form_from_schema, call_api
from app.utils.bank_utils import trans_money, authenticate
import logging
import os
import pandas as pd
from datetime import datetime
from app.controllers.log_controller import log_action
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from werkzeug.utils import secure_filename
from functools import wraps
from io import BytesIO
import json
import requests
from app.models.all_config import AllConfig
from app.models.bank_api_config import BankApiConfig
import re

logger = logging.getLogger(__name__)
bp = Blueprint('academic', __name__)

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_org_users(org_id):
    """获取同一组织下的所有用户ID"""
    org_users = OrgUser.query.filter_by(org_id=org_id).all()
    return [org_user.user_id for org_user in org_users]

def get_user_permission_level(user_id):
    """获取用户的权限级别"""
    user_active = UserActive.query.join(Active).filter(UserActive.user_id == user_id).first()
    return user_active.active.lv if user_active else None

def can_access_private_data(user_id):
    """检查用户是否有权限访问私有数据（权限级别 >= 2）"""
    permission_level = get_user_permission_level(user_id)
    return permission_level >= 2 if permission_level else False

def has_purchased(user_id, content_id, content_type):
    """检查用户是否已购买内容"""
    return UserOrder.query.filter_by(
        user_id=user_id,
        order_id=content_id,
        order_type=content_type
    ).first() is not None

def get_content_price(content_type, content_id=None):
    """获取内容价格"""
    if content_type == 0:  # 学生信息
        if content_id:
            student = Student.query.get(content_id)
            if student:
                return student.price
        return 100
    elif content_type == 1:  # 课程
        if content_id:
            course = Course.query.get(content_id)
            if course:
                return course.price
        return 50
    elif content_type == 2:  # 论文
        if content_id:
            paper = Paper.query.get(content_id)
            if paper:
                return paper.price
        return 80
    return 0

@bp.route('/courses')
@login_required
def courses():
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    org_id = request.args.get('org_id', type=int)
    if not org_id or org_id <=0 :
        org_id = org_user.org_id
    if current_user.is_admin or current_user.is_convener:
        flash('无权访问', 'error')
        return redirect(url_for('main.index'))
    
    
    if not org_user:
        flash('您不属于任何组织', 'error')
        return redirect(url_for('main.index'))
    
    org_users = get_org_users(org_id)
    query = Course.query.filter(Course.user_id.in_(org_users))
    
    # 添加搜索功能
    search = request.args.get('search', '')
    if search:
        query = query.filter(
            db.or_(
                Course.name.ilike(f'%{search}%'),
                Course.describe.ilike(f'%{search}%')
            )
        )
    
    courses = query.all()
    
    # 获取用户购买状态
    purchased_courses = {
        order.order_id: True
        for order in UserOrder.query.filter_by(user_id=current_user.id, order_type=1).all()
    }
    
    return render_template('academic/courses.html', 
                         courses=courses,
                         purchased_courses=purchased_courses,
                         content_type=1,
                         search=search)

@bp.route('/papers')
@login_required
def papers():
    """论文列表页面"""
    # 获取用户所在组织
    org_id = request.args.get('org_id', type=int)
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        flash('您不属于任何组织', 'error')
        return redirect(url_for('main.index'))
    
    # 获取API配置
    config = get_org_api_config(org_id, 2)  # 2 表示论文搜索
    if not config:
        flash('未找到API配置', 'error')
        return redirect(url_for('main.index'))
    
    # 生成动态表单
    form_html = generate_form_from_schema(config.input_schema)
    return render_template('academic/papers.html', form_html=form_html)

@bp.route('/search_papers', methods=['POST'])
@login_required
def search_papers():
    """搜索论文"""
    try:
        # 获取用户所在组织
        org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
        if not org_user:
            return jsonify({'error': '您不属于任何组织'})
        
        # 获取API配置
        config = get_org_api_config(org_user.org_id, 2)  # 2 表示论文搜索
        if not config:
            return jsonify({'error': '未找到API配置'})
        
        # 获取搜索关键词
        data = request.get_json()
        keywords = data.get('keywords')
        if not keywords:
            return jsonify({'error': '搜索关键词不能为空'})
        
        # 确保使用搜索端点
        # 保存原始路径
        original_path = config.api_path
        original_method = config.method
        
        # 修改为搜索路径
        if '/pdf' in config.api_path:
            config.api_path = config.api_path.replace('/pdf', '/search')
        elif not config.api_path.endswith('/search'):
            if config.api_path.endswith('/'):
                config.api_path = config.api_path + 'search'
            else:
                config.api_path = config.api_path + '/search'
        
        # 确保使用POST方法
        config.method = 'POST'
        
        try:
            # 调用API
            result = call_api(config, {'keywords': keywords})
            return jsonify(result)
        finally:
            # 恢复原始设置
            config.api_path = original_path
            config.method = original_method
        
    except Exception as e:
        logger.error(f"搜索论文失败: {str(e)}")
        return jsonify({'error': str(e)})

@bp.route('/download_paper', methods=['POST'])
@login_required
def download_paper():
    """下载论文"""
    try:
        # 获取用户所在组织
        org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
        if not org_user:
            return jsonify({'error': '您不属于任何组织'})
        
        # 获取API配置
        user = UserAccount.query.filter_by(user_id=current_user.id).first()
        # 检查组织余额
        org = Org.query.get(org_user.org_id)
        
        # 获取论文标题
        data = request.get_json()
        title = data.get('title')
        oo_id = data.get('org_id')
        config = get_org_api_config(oo_id, 2)  # 2 表示论文搜索
        if not config:
            return jsonify({'error': '未找到API配置'})
        if not title:
            return jsonify({'error': '论文标题不能为空'})
        if user.quota < config.service_price:
            return jsonify({'error': '余额不足'})
        # 修改API路径和方法
        original_path = config.api_path
        original_method = config.method
        
        # 临时修改路径和方法
        if '/search' in config.api_path:
            config.api_path = config.api_path.replace('/search', '/pdf')
        elif not config.api_path.endswith('/pdf'):
            if config.api_path.endswith('/'):
                config.api_path = config.api_path + 'pdf'
            else:
                config.api_path = config.api_path + '/pdf'
        
        # 重要：设置请求方法为GET
        config.method = 'GET'
        
        try:
            # 直接使用requests库发送请求，而不是通过call_api
            url = f"{config.api_url.rstrip('/')}/{config.api_path.lstrip('/')}"
            print(f"Calling API with GET method: {url}?title={title}")
            
            # 发送GET请求
            response = requests.get(
                url,
                params={'title': title},
                headers={'Accept': 'application/pdf'}
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            
            if response.status_code == 200:
                # 如果API调用成功，扣除余额并创建订单
                
                user.quota -= config.service_price
                db.session.commit()
                
                # 创建订单记录
                order = UserOrder(
                    user_id=current_user.id,
                    order_id=0,
                    order_type=2  # 论文搜索
                )
                db.session.add(order)
                db.session.commit()
                
                # 记录日志
                log_action(current_user.id, f'下载论文成功: {title}')
                
                # 获取文件名和内容类型
                content_type = response.headers.get('Content-Type', 'application/pdf')
                content_disposition = response.headers.get('Content-Disposition', '')
                filename = "paper.pdf"
                
                if 'filename=' in content_disposition:
                    # 解析Content-Disposition获取文件名
                    import re
                    filename_match = re.search(r'filename=["\']?([^"\';]+)', content_disposition)
                    if filename_match:
                        filename = filename_match.group(1)
                
                # 转换PDF为Base64用于前端显示
                import base64
                pdf_data = base64.b64encode(response.content).decode('utf-8')
                
                # 返回结果
                return jsonify({
                    'success': True,
                    'pdf_url': f"data:application/pdf;base64,{pdf_data}",
                    'filename': filename,
                    'content_type': content_type
                })
            else:
                # 处理错误响应
                try:
                    error_detail = response.json()
                    return jsonify({'error': f'API调用失败: {response.status_code}', 'detail': error_detail})
                except:
                    return jsonify({'error': f'API调用失败: {response.status_code}', 'detail': response.text})
                
        finally:
            # 恢复原始设置
            config.api_path = original_path
            config.method = original_method
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"下载论文失败: {str(e)}")
        return jsonify({'error': str(e)})
        
@bp.route('/check_balance')
@login_required
def check_balance():
    """检查组织余额"""
    try:
        # 获取用户所在组织
        org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
        if not org_user:
            return jsonify({'error': '您不属于任何组织'})
        
        org = Org.query.get(org_user.org_id)
        if org.balance < 1:
            return jsonify({'error': '组织余额不足'})
        
        return jsonify({'balance': org.balance})
        
    except Exception as e:
        logger.error(f"检查余额失败: {str(e)}")
        return jsonify({'error': str(e)})

@bp.route('/students')
@login_required
def students():
    if not current_user.is_default and not current_user.is_convener:
        flash('无权访问', 'error')
        return redirect(url_for('main.index'))
    
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        flash('您不属于任何组织', 'error')
        return redirect(url_for('main.index'))
    
    if not can_access_private_data(current_user.id):
        flash('您没有权限访问学生信息', 'error')
        return redirect(url_for('main.index'))
    
    org_users = get_org_users(org_user.org_id)
    query = Student.query.filter(Student.user_id.in_([str(id) for id in org_users]))
    
    # 添加搜索功能
    search = request.args.get('search', '')
    if search:
        query = query.filter(
            db.or_(
                Student.name.ilike(f'%{search}%'),
                Student.in_year.ilike(f'%{search}%'),
                Student.out_year.ilike(f'%{search}%'),
                Student.gpa.ilike(f'%{search}%')
            )
        )
    
    students = query.all()
    
    # 获取用户购买状态
    purchased_students = {
        order.order_id: True
        for order in UserOrder.query.filter_by(user_id=current_user.id, order_type=0).all()
    }
    
    return render_template('academic/students.html', 
                         students=students,
                         purchased_students=purchased_students,
                         content_type=0,
                         search=search)

@bp.route('/courses/create', methods=['GET', 'POST'])
@login_required
def create_course():
    if not current_user.is_default:
        flash('无权访问', 'error')
        return redirect(url_for('main.index'))
    
    # 检查用户权限级别
    if not current_user.has_permission_level(3):
        flash('权限不足，需要权限级别3或以上', 'error')
        return redirect(url_for('academic.courses'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        describe = request.form.get('describe')
        price = request.form.get('price', type=int, default=0)  # 获取价格，默认为0
        
        if not name or not describe:
            flash('请填写完整信息', 'error')
            return redirect(url_for('academic.create_course'))
        
        try:
            course = Course(
                name=name,
                describe=describe,
                user_id=current_user.id
            )
            db.session.add(course)
            db.session.commit()
            flash('课程创建成功', 'success')
            return redirect(url_for('academic.courses'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败: {str(e)}', 'error')
            return redirect(url_for('academic.create_course'))
    
    return render_template('academic/create_course.html')

@bp.route('/papers/create', methods=['GET', 'POST'])
@login_required
def create_paper():
    if not current_user.is_default:
        flash('无权访问', 'error')
        return redirect(url_for('main.index'))
    
    # 检查用户权限级别
    if not current_user.has_permission_level(3):
        flash('权限不足，需要权限级别3或以上', 'error')
        return redirect(url_for('academic.papers'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        describe = request.form.get('describe')
        price = request.form.get('price', type=int, default=0)  # 获取价格，默认为0
        
        if not name or not describe:
            flash('请填写完整信息', 'error')
            return redirect(url_for('academic.create_paper'))
        
        try:
            paper = Paper(
                name=name,
                describe=describe,
                price=price,  # 设置价格
                user_id=current_user.id
            )
            db.session.add(paper)
            db.session.commit()
            flash('论文创建成功', 'success')
            return redirect(url_for('academic.papers'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败: {str(e)}', 'error')
            return redirect(url_for('academic.create_paper'))
    
    return render_template('academic/create_paper.html')

@bp.route('/students/import', methods=['POST'])
@login_required
def import_students():
    """批量导入学生信息"""
    if not current_user.has_permission_level(3):
        return jsonify({'success': False, 'message': '权限不足'})
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '请选择文件'})
    
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': '请选择文件'})
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'success': False, 'message': '请上传Excel文件(.xlsx或.xls格式)'})
    
    try:
        # 保存临时文件
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            
            try:
                # 读取Excel文件，指定引擎
                if file.filename.endswith('.xlsx'):
                    df = pd.read_excel(tmp.name, engine='openpyxl')
                else:
                    df = pd.read_excel(tmp.name, engine='xlrd')
            except Exception as e:
                return jsonify({'success': False, 'message': f'Excel文件格式不正确或已损坏: {str(e)}'})
            finally:
                # 删除临时文件
                os.unlink(tmp.name)
        
        # 检查数据框是否为空
        if df.empty:
            return jsonify({'success': False, 'message': 'Excel文件为空'})
        
        # 检查必要的列是否存在
        required_columns = ['name', 'in_year', 'out_year', 'gpa']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({
                'success': False, 
                'message': f'Excel文件缺少必要的列: {", ".join(missing_columns)}'
            })
        
        # 导入数据
        success_count = 0
        error_count = 0
        error_rows = []
        
        for index, row in df.iterrows():
            try:
                # 检查必要字段是否为空
                if pd.isna(row['name']) or pd.isna(row['in_year']) or pd.isna(row['out_year']) or pd.isna(row['gpa']):
                    error_rows.append(f"第{index+2}行: 存在空值")
                    error_count += 1
                    continue
                
                student = Student(
                    name=str(row['name']).strip(),
                    in_year=str(row['in_year']).strip(),
                    out_year=str(row['out_year']).strip(),
                    gpa=str(row['gpa']).strip(),
                    user_id=str(current_user.id)
                )
                db.session.add(student)
                success_count += 1
            except Exception as e:
                error_rows.append(f"第{index+2}行: {str(e)}")
                error_count += 1
        
        db.session.commit()
        log_action(current_user.id, f'批量导入学生信息: 成功{success_count}条，失败{error_count}条')
        
        message = f'导入完成: 成功{success_count}条，失败{error_count}条'
        if error_rows:
            message += f'\n错误详情:\n' + '\n'.join(error_rows)
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"导入学生信息失败: {str(e)}")
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'})

@bp.route('/students/<int:id>', methods=['DELETE'])
@login_required
def delete_student(id):
    """删除学生信息"""
    if not current_user.has_permission_level(3):
        return jsonify({'success': False, 'message': '权限不足'})
    
    student = Student.query.get_or_404(id)
    try:
        db.session.delete(student)
        db.session.commit()
        log_action(current_user.id, f'删除学生信息: {student.name}')
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除学生信息失败: {str(e)}")
        return jsonify({'success': False, 'message': '删除失败'})

@bp.route('/students/create', methods=['GET', 'POST'])
@login_required
def create_student():
    if not current_user.is_default:
        flash('无权访问', 'error')
        return redirect(url_for('main.index'))
    
    # 检查用户权限级别
    if not current_user.has_permission_level(3):
        flash('权限不足，需要权限级别3或以上', 'error')
        return redirect(url_for('academic.students'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        in_year = request.form.get('in_year')
        out_year = request.form.get('out_year')
        gpa = request.form.get('gpa')
        
        if not all([name, in_year, out_year, gpa]):
            flash('请填写完整信息', 'error')
            return redirect(url_for('academic.create_student'))
        
        try:
            student = Student(
                name=name,
                in_year=in_year,
                out_year=out_year,
                gpa=gpa,
                user_id=str(current_user.id)
            )
            db.session.add(student)
            db.session.commit()
            log_action(current_user.id, f'创建学生信息: {name}')
            flash('学生信息创建成功', 'success')
            return redirect(url_for('academic.students'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败: {str(e)}', 'error')
            return redirect(url_for('academic.create_student'))
    
    return render_template('academic/create_student.html')

@bp.route('/purchase', methods=['POST'])
@login_required
def purchase():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'})
        
        content_id = data.get('content_id')
        order_type = data.get('order_type')
        
        if not content_id or order_type is None:
            return jsonify({'success': False, 'message': '参数错误'})
        
        # 检查是否已购买
        existing_order = UserOrder.query.filter_by(
            user_id=current_user.id,
            order_id=content_id,
            order_type=order_type
        ).first()
        
        if existing_order:
            return jsonify({'success': False, 'message': '您已经购买过此内容'})
        
        # 获取内容价格
        price = get_content_price(order_type, content_id)
        
        # 获取用户账户信息
        user_account = UserAccount.query.filter_by(user_id=current_user.id).first()
        if not user_account:
            return jsonify({'success': False, 'message': '用户账户不存在'})
        
        # 检查用户积分是否足够
        if user_account.quota < price:
            return jsonify({'success': False, 'message': '积分不足'})
        
        try:
            # 扣除积分
            user_account.quota -= price
            
            # 记录购买
            order = UserOrder(
                user_id=current_user.id,
                order_id=content_id,
                order_type=order_type
            )
            
            db.session.add(order)
            db.session.commit()
            
            log_action(current_user.id, f'购买{order_type}成功: {content_id}')
            
            return jsonify({'success': True, 'message': '购买成功'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Purchase error: {str(e)}")
            log_action(current_user.id, f'购买{order_type}失败: {content_id}, 原因: {str(e)}')
            return jsonify({'success': False, 'message': '购买失败，请稍后重试'})
            
    except Exception as e:
        logger.error(f"Purchase request error: {str(e)}")
        return jsonify({'success': False, 'message': '请求处理失败'})

@bp.route('/students/template')
@login_required
def download_template():
    try:
        # 创建示例数据
        data = {
            '姓名': ['张三', '李四'],
            '学号': ['2021001', '2021002']
        }
        df = pd.DataFrame(data)
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='学生信息')
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='学生认证模板.xlsx'
        )
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}")
        flash('生成模板失败', 'error')
        return redirect(url_for('academic.batch_verify_students'))

@bp.route('/students/verify', methods=['GET', 'POST'])
@login_required
def verify_student_page():
    org_id = 0
    org_id = request.args.get('org_id')
    print(org_id)
    if not (current_user.has_permission_level(3) or current_user.has_permission_level(2)):
        flash('无权访问', 'error')
        return redirect(url_for('main.index'))
    
    if not can_access_private_data(current_user.id):
        flash('您没有权限访问学生信息', 'error')
        return redirect(url_for('main.index'))
    # 获取用户所在组织
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        flash('您不属于任何组织', 'error')
        return redirect(url_for('academic.students'))
    
    # 获取API配置
    config = get_org_api_config(org_id, 0)  # 0 表示学生认证
    if not config:
        flash('未找到API配置', 'error')
        return redirect(url_for('academic.students'))
    
    if request.method == 'GET':
        # 生成动态表单
        form_html = generate_form_from_schema(config.input_schema)
        return render_template('academic/verify_student.html', form_html=form_html)
    
    # 处理POST请求
    try:
        # 检查组织余额
        org = Org.query.get(org_user.org_id)
        
        # 处理表单数据 - 从request.form和request.files获取数据
        data = {}
        files = {}
        
        # 从表单获取数据
        for key in request.form:
            if not key.endswith('_base64'):  # 跳过base64字段
                data[key] = request.form[key]
        
        # 处理文件上传
        for key in request.files:
            file = request.files[key]
            if file and file.filename:
                # 保存文件
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                files[key] = file_path
        
        # 调用API
        result = call_api(config, data, files)
        
        # 如果API调用成功，扣除余额并创建订单
        if 'error' not in result:
            
            # 创建订单记录
            order = UserOrder(
                user_id=current_user.id,
                order_id=0,
                order_type=0
            )
            db.session.add(order)
            db.session.commit()
            
            # 记录日志
            log_action(current_user.id, f'学生认证成功: {data}')
        
        return jsonify(result)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"学生认证失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/students/search', methods=['GET', 'POST'])
@login_required
def search_students_page():
    org_id = 0
    org_id = request.args.get('org_id')
    print(org_id)
    if not (current_user.has_permission_level(3) or current_user.has_permission_level(2)):
        flash('无权访问', 'error')
        return redirect(url_for('main.index'))
    
    if not can_access_private_data(current_user.id):
        flash('您没有权限访问学生信息', 'error')
        return redirect(url_for('main.index'))
    # 获取用户所在组织
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        flash('您不属于任何组织', 'error')
        return redirect(url_for('academic.students'))
    
    # 获取API配置
    config = get_org_api_config(org_id, 1)  # 1 表示学生查询
    if not config:
        flash('未找到API配置', 'error')
        return redirect(url_for('academic.students'))
    
    if request.method == 'GET':
        # 生成动态表单
        form_html = generate_form_from_schema(config.input_schema)
        return render_template('academic/search_students.html', form_html=form_html)
    
    # 处理POST请求
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
        
        # 检查组织余额
        org = Org.query.get(org_user.org_id)
        
        # 构建API URL
        url = f"{config.api_url.rstrip('/')}/{config.api_path.lstrip('/')}"
        
        # 直接使用原始数据，不做任何修改
        print(f"Sending JSON to API: {json.dumps(data)}")
        response = requests.post(
            url,
            json=data,  # 直接发送原始JSON数据
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        # 处理API响应
        if response.status_code == 200:
            # 如果API调用成功，扣除余额并创建订单

            
            # 创建订单记录
            order = UserOrder(
                user_id=current_user.id,
                order_id=0,
                order_type=1  # 学生查询
            )
            db.session.add(order)
            db.session.commit()
            
            # 记录日志
            log_action(current_user.id, f'学生查询成功: {data}')
            
            # 返回API响应
            try:
                return jsonify(response.json())
            except:
                return jsonify({'error': '无效的API响应格式'})
        else:
            # 尝试获取错误详情
            try:
                error_detail = response.json()
                return jsonify({'error': f'API调用失败: {response.status_code}', 'detail': error_detail})
            except:
                return jsonify({'error': f'API调用失败: {response.status_code}', 'detail': response.text})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"学生查询失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/students/<int:student_id>')
@login_required
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template('academic/student_detail.html', student=student)

@bp.route('/org/config', methods=['GET', 'POST'])
@login_required
def org_config():
    # 检查用户是否为convener
    if not current_user.is_convener:
        flash('您没有权限访问此页面', 'error')
        return redirect(url_for('main.index'))
    
    # 获取用户所在组织
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        flash('您不属于任何组织', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'GET':
        # 获取或创建组织配置
        configs = []
        for feature_type in range(4):  # 0: 论文, 1: 课程, 2: 学生认证, 3: 学生搜索
            config = OrgConfig.query.filter_by(
                org_id=org_user.org_id,
                feature_type=feature_type
            ).first()
            
            if not config:
                config = OrgConfig(
                    org_id=org_user.org_id,
                    feature_type=feature_type,
                    is_enabled=True,
                    service_price=0  # 设置默认服务价格
                )
                db.session.add(config)
                db.session.commit()
            
            configs.append(config)
        
        return render_template('academic/org_config.html', configs=configs)
    
    # 处理POST请求
    try:
        # 更新配置
        feature_types = {
            'papers': 0,
            'courses': 1,
            'verify': 2,
            'search': 3
        }
        
        for feature_name, feature_type in feature_types.items():
            config = OrgConfig.query.filter_by(
                org_id=org_user.org_id,
                feature_type=feature_type
            ).first()
            
            if config:
                # 更新启用状态
                config.is_enabled = request.form.get(feature_name) == 'on'
                
                # 更新服务价格
                price = request.form.get(f'{feature_name}_price')
                if price is not None:
                    try:
                        config.service_price = int(price)
                    except ValueError:
                        config.service_price = 0
        
        db.session.commit()
        flash('配置已保存', 'success')
        return redirect(url_for('academic.org_config'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新组织配置失败: {str(e)}")
        flash('保存配置失败，请重试', 'error')
        return redirect(url_for('academic.org_config'))

# 添加检查功能是否启用的装饰器
def check_feature_enabled(feature_type):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取用户所在组织
            org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
            if not org_user:
                flash('您不属于任何组织', 'error')
                return redirect(url_for('main.index'))
            
            # 检查功能是否启用
            config = OrgConfig.query.filter_by(
                org_id=org_user.org_id,
                feature_type=feature_type
            ).first()
            
            if not config or not config.is_enabled:
                flash('此功能未启用', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@bp.route('/students/batch_verify', methods=['GET', 'POST'])
@login_required
def batch_verify_students():
    """处理批量学生认证请求"""
    if request.method == 'GET':
        return render_template('academic/batch_verify.html')
        
    org_id = 0
    org_id = request.args.get('org_id')
    print(org_id)
    if not (current_user.has_permission_level(3) or current_user.has_permission_level(2)):
        flash('无权访问', 'error')
        return redirect(url_for('main.index'))
    
    if not can_access_private_data(current_user.id):
        flash('您没有权限访问学生信息', 'error')
        return redirect(url_for('main.index'))
    # 获取用户所在组织
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        flash('您不属于任何组织', 'error')
        return redirect(url_for('academic.students'))
    
    # 获取API配置
    config = get_org_api_config(org_id, 0)  # 0 表示学生认证
    if not config:
        flash('未找到API配置', 'error')
        return redirect(url_for('academic.students'))
        
    if 'excel_file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400
        
    excel_file = request.files['excel_file']
    if not excel_file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': '请上传Excel文件(.xlsx或.xls)'}), 400
        
    try:            
        # 读取Excel文件
        df = pd.read_excel(excel_file)
        
        # 验证数据格式
        if len(df.columns) < 2:
            return jsonify({'error': 'Excel文件格式错误，需要至少两列：学生ID和学生姓名'}), 400
            
        # 提取学生信息并验证
        students = []
        for _, row in df.iterrows():
            student_id = str(row[0]).strip()
            student_name = str(row[1]).strip()
            
            if not student_id or not student_name:
                continue
                
            students.append({
                'id': student_id,
                'name': student_name
            })
            
        if not students:
            return jsonify({'error': '未找到有效的学生信息'}), 400
            
        # 检查组织余额
        if org.balance < len(students):
            return jsonify({'error': '组织余额不足'}), 400
            
        # 批量验证学生
        results = []
        success_count = 0
        error_count = 0
        
        for student in students:
            try:
                # 准备请求数据
                data = {
                    'student_id': student['id'],
                    'student_name': student['name']
                }
                
                # 调用API
                result = call_api(config, data)
                
                if 'error' not in result:
                    # 创建订单记录
                    order = UserOrder(
                        user_id=current_user.id,
                        order_id=0,
                        order_type=0
                    )
                    db.session.add(order)
                    success_count += 1
                    results.append({
                        'student_id': student['id'],
                        'student_name': student['name'],
                        'status': 'success',
                        'message': '验证成功'
                    })
                else:
                    error_count += 1
                    results.append({
                        'student_id': student['id'],
                        'student_name': student['name'],
                        'status': 'error',
                        'message': result.get('error', '验证失败')
                    })
                    
            except Exception as e:
                error_count += 1
                results.append({
                    'student_id': student['id'],
                    'student_name': student['name'],
                    'status': 'error',
                    'message': str(e)
                })
        
        # 提交所有成功的订单
        db.session.commit()
        
        # 记录日志
        log_action(current_user.id, f'批量学生认证完成: 成功{success_count}条，失败{error_count}条')
        
        return jsonify({
            'success': True,
            'total': len(students),
            'success_count': success_count,
            'error_count': error_count,
            'results': results
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"批量学生认证失败: {str(e)}")
        return jsonify({'error': f'处理Excel文件时出错：{str(e)}'}), 400

@bp.route('/org_api_config')
@login_required
def org_api_config():
    # 获取用户所在组织
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        flash('您不属于任何组织', 'error')
        return redirect(url_for('academic.index'))
    
    # 获取组织的所有API配置并转换为字典
    configs = {}
    for config in OrgApiConfig.query.filter_by(org_id=org_user.org_id).all():
        try:
            # 确保JSON schema是有效的JSON
            input_schema = json.loads(config.input_schema) if config.input_schema else {}
            output_schema = json.loads(config.output_schema) if config.output_schema else {}
            
            configs[str(config.feature_type)] = {
                'api_url': config.api_url or '',
                'api_path': config.api_path or '',
                'method': config.method or 'POST',
                'input_schema': json.dumps(input_schema, ensure_ascii=False),
                'output_schema': json.dumps(output_schema, ensure_ascii=False)
            }
        except json.JSONDecodeError:
            # 如果JSON解析失败，使用空对象
            configs[str(config.feature_type)] = {
                'api_url': config.api_url or '',
                'api_path': config.api_path or '',
                'method': config.method or 'POST',
                'input_schema': '{}',
                'output_schema': '{}'
            }
    
    return render_template('academic/org_api_config.html', configs=configs)

@bp.route('/org/api_config/save', methods=['POST'])
@login_required
def save_api_config():
    if not current_user.has_permission_level(3):
        return jsonify({'success': False, 'message': '无权访问'})
    
    # 获取用户所在组织
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        return jsonify({'success': False, 'message': '您不属于任何组织'})
    
    try:
        # 验证JSON schema格式
        input_schema = request.form.get('input_schema')
        output_schema = request.form.get('output_schema')
        feature_type = int(request.form.get('feature_type'))
        json.loads(input_schema)
        json.loads(output_schema)
        
        # 获取或创建配置
        config = OrgApiConfig.query.filter_by(
            org_id=org_user.org_id,
            feature_type=feature_type
        ).first()
        
        if not config:
            config = OrgApiConfig(
                org_id=org_user.org_id,
                feature_type=feature_type
            )
            db.session.add(config)
        
        # 更新配置
        config.api_url = request.form.get('api_url')
        config.api_path = request.form.get('api_path')
        config.method = request.form.get('method')
        config.input_schema = input_schema
        config.output_schema = output_schema
        config.service_price = request.form.get('service_price')
        
        db.session.commit()
        flash('API配置已保存', 'success')
        
    except json.JSONDecodeError:
        flash('JSON格式错误', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'保存失败: {str(e)}', 'error')
    
    return redirect(url_for('academic.org_api_config'))

@bp.route('/api/test/<int:feature_type>', methods=['POST'])
@login_required
def test_api(feature_type):
    if not current_user.is_convener:
        return jsonify({'success': False, 'message': '无权访问'})
    
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        return jsonify({'success': False, 'message': '您不属于任何组织'})
    
    config = OrgApiConfig.query.filter_by(
        org_id=org_user.org_id,
        feature_type=feature_type
    ).first()
    
    if not config:
        return jsonify({'success': False, 'message': '未找到API配置'})
    
    try:
        # 发送API请求
        url = config.api_url + config.api_path
        headers = {'Content-Type': 'application/json'}
        
        if config.method == 'GET':
            response = requests.get(url, params=request.json)
        else:
            response = requests.post(url, json=request.json, headers=headers)
        
        return jsonify({
            'success': True,
            'data': response.json()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'请求失败: {str(e)}'
        })

@bp.route('/api/config/<int:feature_type>')
@login_required
def get_api_config(feature_type):
    # 获取用户所在组织
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        return jsonify({'success': False, 'message': '您不属于任何组织'})
    
    config = OrgApiConfig.query.filter_by(
        org_id=org_user.org_id,
        feature_type=feature_type
    ).first()
    
    if not config:
        return jsonify({'success': False, 'message': '未找到API配置'})
    
    return jsonify({
        'success': True,
        'data': {
            'api_url': config.api_url,
            'api_path': config.api_path,
            'method': config.method,
            'input_schema': config.input_schema,
            'output_schema': config.output_schema
        }
    })

@bp.route('/services')
@login_required
def services():
    """显示所有组织的服务"""
    # 获取当前用户所在组织
    current_org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not current_org_user:
        flash('您不属于任何组织', 'error')
        return redirect(url_for('main.index'))
    
    current_org = current_org_user.org
    
    # 获取所有组织及其配置
    orgs = Org.query.all()
    org_services = []
    
    for org in orgs:
        if org.id == current_org.id:
            continue  # 跳过当前用户所在组织
            
        # 获取组织的服务配置
        configs = OrgConfig.query.filter_by(org_id=org.id).all()
        enabled_services = [config for config in configs if config.is_enabled]
        
        if enabled_services:
            org_services.append({
                'org': org,
                'services': enabled_services
            })
    
    return render_template('academic/services.html', 
                         current_org=current_org,
                         org_services=org_services)

@bp.route('/use_service/<int:org_id>/<int:service_id>', methods=['POST'])
@login_required
def use_service(org_id, service_id):
    """使用其他组织的服务"""
    try:
        # 获取当前用户所在组织
        current_org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
        if not current_org_user:
            return jsonify({'error': '您不属于任何组织'})
        
        current_org = current_org_user.org
        
        # 获取服务提供组织
        service_org = Org.query.get(org_id)
        if not service_org:
            return jsonify({'error': '服务组织不存在'})
        
        # 获取服务配置
        service_config = OrgConfig.query.filter_by(
            org_id=org_id,
            id=service_id
        ).first()
        
        if not service_config or not service_config.is_enabled:
            return jsonify({'error': '服务不可用'})
        
        # 检查当前组织余额
        if current_org.balance < 1:
            return jsonify({'error': '组织余额不足'})
        
        # 执行转账
        success, message = trans_money(current_org, service_org, 1)
        if not success:
            return jsonify({'error': message})
        
        # 更新余额
        current_org.balance -= 1
        service_org.balance += 1
        
        # 创建订单记录
        order = UserOrder(
            user_id=current_user.id,
            org_id=service_org.id,
            service_id=service_id,
            amount=1
        )
        db.session.add(order)
        db.session.commit()
        
        # 记录日志
        logger.info(f"用户 {current_user.name} 使用组织 {service_org.name} 的服务 {service_config.feature_type}")
        
        return jsonify({'success': True, 'message': '服务使用成功'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"使用服务失败: {str(e)}")
        return jsonify({'error': str(e)})

@bp.route('/transform',methods=['POST'])
@login_required
def transform():
    data = request.get_json()
    oid = data.get('org_id')
    type = data.get('type')
    config = OrgConfig.query.filter_by(org_id=oid,feature_type=type).first()
    if not config:
        return jsonify({'error': '未找到API配置'})
    oorg = Org.query.get(oid)
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        return jsonify({'error': '您不属于任何组织'})

    org = Org.query.get(org_user.org_id)
    if oid != org_user.org_id:
        trans_money(org, oorg, config.service_price)
    return jsonify({'success': True})

@bp.route('/org/bank_info')
@login_required
def org_bank_info():
    """显示组织银行账户信息页面"""
    if not current_user.is_convener:
        flash('您没有权限访问此页面', 'error')
        return redirect(url_for('main.index'))
    
    # 获取用户所在组织
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        flash('您不属于任何组织', 'error')
        return redirect(url_for('main.index'))
    
    org = Org.query.get(org_user.org_id)
    if not org:
        flash('组织不存在', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('academic/org_bank_info.html', org=org)

@bp.route('/org/bank_info/update', methods=['POST'])
@login_required
def update_org_bank_info():
    """更新组织银行账户信息"""
    if not current_user.is_convener:
        return jsonify({'success': False, 'message': '您没有权限执行此操作'})
    
    # 获取用户所在组织
    org_user = OrgUser.query.filter_by(user_id=current_user.id).first()
    if not org_user:
        return jsonify({'success': False, 'message': '您不属于任何组织'})
    
    org = Org.query.get(org_user.org_id)
    if not org:
        return jsonify({'success': False, 'message': '组织不存在'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'})
        
        # 更新银行账户信息
        org.bank_name = data.get('bank_name')
        org.bank_account = data.get('bank_account')
        org.bank_password = data.get('bank_password')
        
        db.session.commit()
        
        # 记录日志
        log_action(current_user.id, '更新组织银行账户信息')
        
        authenticate(org)
        return jsonify({'success': True, 'message': '银行账户信息更新成功'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新组织银行账户信息失败: {str(e)}")
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'})

@bp.route('/all_config')
@login_required
def all_config():
    """显示基础收费设置页面"""
    if not current_user.is_e_admin:
        flash('您没有权限访问此页面', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # 获取或创建配置
        config = AllConfig.query.first()
        if not config:
            # 如果没有配置，创建一个新的
            config = AllConfig()
            config.all = 0
            config.private = 0
            db.session.add(config)
            db.session.commit()
            # 重新查询以确保数据已保存
            config = AllConfig.query.first()
        
        if not config:
            raise Exception("无法创建或获取配置")
            
        return render_template('academic/all_config.html', config=config)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"获取基础收费设置失败: {str(e)}")
        flash('获取设置失败，请重试', 'error')
        return redirect(url_for('main.index'))

@bp.route('/all_config/update', methods=['POST'])
@login_required
def update_all_config():
    """更新基础收费设置"""
    if not current_user.is_e_admin:
        return jsonify({'success': False, 'message': '您没有权限执行此操作'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'})
        
        # 获取或创建配置
        config = AllConfig.query.first()
        if not config:
            config = AllConfig()
            db.session.add(config)
        
        # 更新配置
        try:
            all_price = int(data.get('all', 0))
            private_price = int(data.get('private', 0))
        except ValueError:
            return jsonify({'success': False, 'message': '价格必须是有效的数字'})
        
        config.all = all_price
        config.private = private_price
        
        db.session.commit()
        
        # 记录日志
        log_action(current_user.id, f'更新基础收费设置: all={all_price}, private={private_price}')
        
        return jsonify({'success': True, 'message': '基础收费设置已更新'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新基础收费设置失败: {str(e)}")
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'})

@bp.route('/bank_api_config')
@login_required
def bank_api_config():
    """显示银行接口配置页面"""
    if not current_user.is_e_admin:
        flash('您没有权限访问此页面', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # 获取认证接口配置
        auth_config = BankApiConfig.query.filter_by(feature_type=1).first()
        if not auth_config:
            auth_config = BankApiConfig(
                feature_type=1,
                api_url='http://172.16.160.88:8001',
                api_path='/hw/bank/authenticate',
                method='POST',
                input_schema=json.dumps({
                    "bank": "string",
                    "account_name": "string",
                    "account_number": "string",
                    "password": "string"
                }),
                output_schema=json.dumps({"status": "success"})
            )
            db.session.add(auth_config)
            db.session.commit()
        
        # 获取转账接口配置
        transfer_config = BankApiConfig.query.filter_by(feature_type=2).first()
        if not transfer_config:
            transfer_config = BankApiConfig(
                feature_type=2,
                api_url='http://172.16.160.88:8001',
                api_path='/hw/bank/transfer',
                method='POST',
                input_schema=json.dumps({
                    "from_bank": "string",
                    "from_name": "string",
                    "from_account": "string",
                    "password": "string",
                    "to_bank": "string",
                    "to_name": "string",
                    "to_account": "string",
                    "amount": "int"
                }),
                output_schema=json.dumps({"status": "success"})
            )
            db.session.add(transfer_config)
            db.session.commit()
        
        return render_template('academic/bank_api_config.html', 
                             auth_config=auth_config,
                             transfer_config=transfer_config)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"获取银行接口配置失败: {str(e)}")
        flash('获取配置失败，请重试', 'error')
        return redirect(url_for('main.index'))

@bp.route('/bank_api_config/update', methods=['POST'])
@login_required
def update_bank_api_config():
    """更新银行接口配置"""
    if not current_user.is_e_admin:
        return jsonify({'success': False, 'message': '您没有权限执行此操作'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'})
        
        feature_type = int(data.get('featureType'))
        if feature_type not in [1, 2]:
            return jsonify({'success': False, 'message': '无效的接口类型'})
        
        # 获取或创建配置
        config = BankApiConfig.query.filter_by(feature_type=feature_type).first()
        if not config:
            config = BankApiConfig(feature_type=feature_type)
            db.session.add(config)
        
        # 更新配置
        config.api_url = data.get('apiUrl')
        config.api_path = data.get('apiPath')
        config.method = data.get('method')
        config.input_schema = data.get('inputSchema')
        config.output_schema = data.get('outputSchema')
        
        db.session.commit()
        
        # 记录日志
        log_action(current_user.id, f'更新银行接口配置: type={feature_type}')
        
        return jsonify({'success': True, 'message': '配置更新成功'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新银行接口配置失败: {str(e)}")
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'})

@bp.route('/bank_api_config/import', methods=['POST'])
@login_required
def import_bank_api_config():
    """从txt文件导入银行接口配置"""
    if not current_user.is_e_admin:
        return jsonify({'success': False, 'message': '您没有权限执行此操作'})
    
    if 'configFile' not in request.files:
        return jsonify({'success': False, 'message': '未上传文件'})
    
    file = request.files['configFile']
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'})
    
    if not file.filename.endswith('.txt'):
        return jsonify({'success': False, 'message': '请上传txt文件'})
    
    try:
        # 读取文件内容
        content = file.read().decode('utf-8')
        logger.info(f"读取文件内容成功，长度: {len(content)}")
        
        # 解析基础URL
        url_match = re.search(r'url:\s*(.+?)(?:\n|$)', content)
        if not url_match:
            logger.error("未找到基础URL")
            return jsonify({'success': False, 'message': '未找到基础URL'})
        base_url = url_match.group(1).strip()
        logger.info(f"解析到基础URL: {base_url}")
        
        # 解析接口配置
        interfaces = []
        current_interface = None
        current_section = None
        json_buffer = []
        
        def fix_json_format(json_str):
            """修复JSON格式"""
            # 处理多个JSON对象用/连接的情况
            if '/' in json_str:
                parts = json_str.split('/')
                # 使用第一个JSON对象
                json_str = parts[0].strip()
            
            # 修复缺少逗号的问题
            json_str = re.sub(r'}\s*{', '},{', json_str)
            
            # 修复缺少逗号的问题（在属性之间）
            json_str = re.sub(r'"\s*"', '","', json_str)
            
            # 修复类型值
            json_str = re.sub(r':\s*int\b', ': "integer"', json_str)
            json_str = re.sub(r':\s*string\b', ': "string"', json_str)
            json_str = re.sub(r':\s*float\b', ': "number"', json_str)
            json_str = re.sub(r':\s*bool\b', ': "boolean"', json_str)
            
            # 确保JSON字符串以}结尾
            if not json_str.strip().endswith('}'):
                json_str = json_str.strip() + '}'
            
            return json_str
        
        def process_json_section():
            """处理当前JSON部分"""
            if current_interface and current_section in ['input', 'output']:
                try:
                    json_str = ''.join(json_buffer)
                    json_str = fix_json_format(json_str)
                    current_interface[current_section] = json_str
                    json.loads(current_interface[current_section])  # 验证JSON格式
                    if current_section == 'output':
                        interfaces.append(current_interface)
                    return True
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {str(e)}")
                    return False
            return True
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            logger.debug(f"处理行: {line}")
            
            if line.startswith('Interface'):
                # 处理之前的接口配置
                if not process_json_section():
                    return jsonify({'success': False, 'message': f'{current_section}参数JSON格式错误'})
                
                # 开始新的接口配置
                interface_num = int(line.split()[1].rstrip(':'))
                current_interface = {'type': interface_num}
                current_section = None
                json_buffer = []
                logger.info(f"开始解析接口 {interface_num}")
                
            elif current_interface is not None:
                if line.startswith('method:'):
                    current_interface['method'] = line.split(':', 1)[1].strip()
                    current_section = 'method'
                elif line.startswith('path:'):
                    current_interface['path'] = line.split(':', 1)[1].strip()
                    current_section = 'path'
                elif line.startswith('input:'):
                    # 处理之前的section
                    if not process_json_section():
                        return jsonify({'success': False, 'message': f'{current_section}参数JSON格式错误'})
                    current_section = 'input'
                    json_buffer = [line.split(':', 1)[1].strip()]
                elif line.startswith('output:'):
                    # 处理之前的section
                    if not process_json_section():
                        return jsonify({'success': False, 'message': f'{current_section}参数JSON格式错误'})
                    current_section = 'output'
                    json_buffer = [line.split(':', 1)[1].strip()]
                elif current_section in ['input', 'output']:
                    json_buffer.append(line)
        
        # 处理最后一个接口
        if not process_json_section():
            return jsonify({'success': False, 'message': f'{current_section}参数JSON格式错误'})
        
        if not interfaces:
            logger.error("未找到有效的接口配置")
            return jsonify({'success': False, 'message': '未找到有效的接口配置'})
        
        logger.info(f"解析到 {len(interfaces)} 个接口配置")
        logger.info(f"接口配置: {interfaces}")
        
        # 更新数据库
        for interface in interfaces:
            try:
                # 验证JSON格式
                input_json = json.loads(interface['input'])
                output_json = json.loads(interface['output'])
                
                config = BankApiConfig.query.filter_by(feature_type=interface['type']).first()
                if not config:
                    config = BankApiConfig(feature_type=interface['type'])
                    db.session.add(config)
                
                config.api_url = base_url
                config.api_path = interface['path']
                config.method = interface['method']
                config.input_schema = json.dumps(input_json, ensure_ascii=False)
                config.output_schema = json.dumps(output_json, ensure_ascii=False)
                
                logger.info(f"更新接口 {interface['type']} 配置成功")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {str(e)}")
                return jsonify({'success': False, 'message': f'接口 {interface["type"]} 的JSON格式错误: {str(e)}'})
            except Exception as e:
                logger.error(f"更新接口 {interface['type']} 配置失败: {str(e)}")
                return jsonify({'success': False, 'message': f'更新接口 {interface["type"]} 配置失败: {str(e)}'})
        
        db.session.commit()
        logger.info("所有配置更新成功")
        
        # 记录日志
        log_action(current_user.id, '导入银行接口配置')
        
        return jsonify({'success': True, 'message': '配置导入成功'})
        
    except UnicodeDecodeError:
        logger.error("文件编码错误")
        return jsonify({'success': False, 'message': '文件编码错误，请使用UTF-8编码'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"导入银行接口配置失败: {str(e)}")
        return jsonify({'success': False, 'message': f'导入失败：{str(e)}'})