import os
from flask import Flask, render_template # (수정) render_template 추가
from sqlalchemy import text
from apscheduler.schedulers.background import BackgroundScheduler
import traceback # (신규)

# (신규) current_user 임포트
from flask_login import LoginManager, current_user

from .models import db, User 

# (기존) LoginManager 인스턴스 생성
login_manager = LoginManager()
login_manager.login_view = 'auth.login' 
login_manager.login_message = '로그인이 필요합니다.'
login_manager.login_message_category = 'info'


def keep_db_awake(app):
    try:
        with app.app_context():
            # (수정) 1개의 DB(기본)에만 쿼리
            db.session.execute(text('SELECT 1'))
            print("Neon DB keep-awake (from scheduler).")
    except Exception as e:
        print(f"Keep-awake scheduler error: {e}")

# (기존) flask-login 사용자 로더
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id)) 

def create_app(config_class):
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config_class)
    
    # (삭제) SQLALCHEMY_BINDS 설정
    
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = config_class.SQLALCHEMY_ENGINE_OPTIONS

    db.init_app(app)
    login_manager.init_app(app) # (기존) LoginManager 앱에 등록

    # --- 블루프린트 등록 ---
    from .routes_ui import ui_bp 
    from .routes_api import api_bp
    from .routes_auth import auth_bp 
    
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp) 
    
    # (삭제) @app.before_request ...

    # --- Context Processors ---
    IMAGE_URL_PREFIX = 'https://files.ebizway.co.kr/files/10249/Style/'
    @app.context_processor
    def inject_image_url_prefix():
        return dict(IMAGE_URL_PREFIX=IMAGE_URL_PREFIX)

    @app.context_processor
    def inject_global_vars():
        """(수정) 로그인한 유저의 매장 이름을 전역으로 주입"""
        shop_name = 'FLOWORK' # 기본값 (로그인 안했을 때)
        try:
            if current_user.is_authenticated:
                # (수정) current_user에서 매장 이름을 가져옴
                shop_name = current_user.store.store_name
        except Exception as e:
            # (참고) DB 연결 실패 등 예외 처리
            print(f"Warning: Could not fetch shop name. Error: {e}")
        return dict(shop_name=shop_name)

    # --- (수정) 전역 에러 핸들러 ---
    @app.errorhandler(404)
    def not_found_error(error):
        """404 Not Found 오류 처리"""
        # (수정) 404.html 템플릿 렌더링
        return render_template('404.html', 
                               error_description=getattr(error, 'description', '페이지를 찾을 수 없습니다.')), 404

    @app.errorhandler(500)
    def internal_error(error):
        """500 Internal Server Error 처리"""
        db.session.rollback()
        print(f"Internal Server Error: {error}")
        traceback.print_exc() # (신규) 상세 오류 로그 출력
        # (수정) 500.html 템플릿 렌더링
        return render_template('500.html', 
                               error_message=str(error)), 500
    
    # (신규) 403 권한 없음 오류 처리
    @app.errorhandler(403)
    def forbidden_error(error):
        """403 Forbidden (권한 없음) 오류 처리"""
        return render_template('403.html',
                               error_description=getattr(error, 'description', '이 작업에 대한 권한이 없습니다.')), 403

    # --- CLI Commands ---
    @app.cli.command("init-db")
    def init_db_command():
        """(수정) *모든* DB 테이블을 생성/검증합니다."""
        with app.app_context():
            print("Creating/Checking all tables in default database...")
            # (수정) 모든 모델 임포트
            from .models import (
                Brand, Store, User, Product, Variant, StoreStock, 
                Order, OrderProcessing, Setting, Announcement,
                Staff, ScheduleEvent # (신규) Staff, ScheduleEvent 임포트
            )
            db.create_all()
        print("✅ 모든 DB 테이블 초기화/검증 완료.")
    
    # (삭제) 모든 init-db-*, create-*-tables 명령어
    
    
    if os.environ.get('RENDER'):
        scheduler = BackgroundScheduler(daemon=True)
        # (수정) 스케줄러 간격을 4분 -> 3분으로 변경
        scheduler.add_job(lambda: keep_db_awake(app), 'interval', minutes=3)
        scheduler.start()
        print("APScheduler started (Render environment).")
    else:
        print("APScheduler skipped (Not in RENDER environment).")
    
    return app