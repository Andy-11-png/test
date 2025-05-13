from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_mail import Mail
import logging
from logging.handlers import RotatingFileHandler
import os
from app.config import Config

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 初始化数据库
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    
    app.config.from_object(config_class)
    
    # 配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 邮件配置
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'andy20040115@gmail.com'  # 替换为你的Gmail邮箱
    app.config['MAIL_PASSWORD'] = 'udoo quxh yigu zxin'     # 替换为你的应用专用密码
    app.config['MAIL_DEFAULT_SENDER'] = 'andy20040115@gmail.com'  # 替换为你的Gmail邮箱
    

    # 照片文件夹配置
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)# 确保目录存在


    # 初始化数据库
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'
    
    # 配置日志
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log',
                                         maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')
    
    # 初始化定时任务

    
    @login_manager.user_loader
    def load_user(user_id):
        logger.debug(f"Loading user with ID: {user_id}")
        try:
            from app.models import User
            user = User.query.get(int(user_id))
            if user:
                roles = [ur.role.value for ur in user.user_roles]
                logger.debug(f"User loaded: {user.name}, roles: {roles}, status: {user.status}")
            else:
                logger.debug(f"No user found with ID: {user_id}")
            return user
        except Exception as e:
            logger.error(f"Error loading user: {str(e)}")
            return None
    
    # 注册蓝图
    from app.controllers.main_controller import bp as main_bp
    from app.controllers.question_controller import bp as question_bp
    from app.controllers.user_controller import bp as user_bp
    from app.controllers.purchase_controller import bp as purchase_bp
    from app.controllers.academic_controller import bp as academic_bp
    from app.controllers.log_controller import bp as log_bp
    from app.controllers.auth import bp as auth_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(question_bp, url_prefix='/questions')
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(purchase_bp, url_prefix='/purchases')
    app.register_blueprint(academic_bp, url_prefix='/academic')
    app.register_blueprint(log_bp, url_prefix='/logs')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)
    
    return app 