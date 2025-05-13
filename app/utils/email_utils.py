from flask_mail import Message
from app import mail
from app.models.email_verify import EmailVerify
from app import db
import random
import string
import time
import logging
from threading import Thread
from flask import current_app

def generate_verification_code():
    """生成6位随机验证码"""
    return ''.join(random.choices(string.digits, k=6))

def send_async_email(app, msg):
    """在后台线程中异步发送邮件"""
    with app.app_context():
        try:
            mail.send(msg)
            logging.info(f"异步邮件成功发送到 {msg.recipients}")
        except Exception as e:
            logging.error(f"异步邮件发送失败: {str(e)}")

def send_verification_email(email):
    """发送验证码邮件"""
    try:
        # 生成验证码
        code = generate_verification_code()
        
        # 创建验证码记录
        verify = EmailVerify(email=email, code=code)
        db.session.add(verify)
        db.session.commit()
        
        # 创建邮件消息
        msg = Message(
            '邮箱验证码',
            recipients=[email],
            body=f'您的验证码是: {code}，有效期为5分钟。'
        )
        
        # 添加重试机制
        max_retries = 3
        retry_delay = 2  # 秒
        last_error = None
        
        for attempt in range(max_retries):
            try:
                mail.send(msg)
                logging.info(f"成功发送验证码到 {email}")
                return True
            except Exception as e:
                last_error = e
                logging.warning(f"发送验证码尝试 {attempt+1}/{max_retries} 失败: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        # 所有重试都失败
        logging.error(f"发送验证码到 {email} 最终失败: {str(last_error)}")
        return False
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"发送验证码失败: {str(e)}")
        return False

def verify_email_code(email, code):
    """验证邮箱验证码"""
    verify = EmailVerify.query.filter_by(
        email=email,
        code=code,
        is_used=False
    ).order_by(EmailVerify.created_at.desc()).first()
    
    if not verify:
        return False
    
    verify.mark_as_used()
    return True