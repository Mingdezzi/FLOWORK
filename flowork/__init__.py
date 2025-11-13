import os
from flask import Flask
from sqlalchemy import text
from apscheduler.schedulers.background import BackgroundScheduler
from flask_wtf.csrf import CSRFProtect  # [수정 1-3] CSRF 보호 모듈 임포트

from .extensions import db, login_manager
from .models import User 
from .commands import init_db_command

# [수정 1-3] CSRF 객체 생성
csrf = CSRFProtect()

login_manager.login_view = 'auth.login' 
login_manager.login_message = '로그인이 필요합니다.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id)) 

def keep_db_awake(app):
    """DB 연결 끊김 방지용 스케줄러 작업"""
    try:
        with app.app_context():
            db.session.execute(text('SELECT 1'))
            print("Neon DB keep-awake (from scheduler).")
    except Exception as e:
        print(f"Keep-awake scheduler error: {e}")

def create_app(config_class):
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config_class)
    
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = config_class.SQLALCHEMY_ENGINE_OPTIONS

    # 1. 확장 모듈 초기화
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app) # [수정 1-3] CSRF 보호 초기화

    # 2. CLI 명령어 등록
    app.cli.add_command(init_db_command)

    # 3. 블루프린트 등록
    from .blueprints.ui import ui_bp 
    from .blueprints.api import api_bp
    from .blueprints.auth import auth_bp 
    
    # CSRF 예외 처리 (필요한 경우)
    # api_bp의 특정 라우트만 예외 처리하고 싶다면 csrf.exempt(api_bp) 등을 사용할 수 있으나,
    # 보안을 위해 모든 POST 요청에 토큰을 검증하는 것이 원칙입니다.
    
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp) 
    
    # 4. 스케줄러 설정 (Render 환경)
    if os.environ.get('RENDER'):
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(lambda: keep_db_awake(app), 'interval', minutes=3)
        scheduler.start()
        print("APScheduler started (Render environment).")
    else:
        print("APScheduler skipped (Not in RENDER environment).")
    
    return app