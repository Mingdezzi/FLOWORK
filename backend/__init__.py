from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from .config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 플러그인 초기화
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app) # SPA(Frontend)와의 통신을 위해 CORS 허용

    # API 블루프린트 등록
    from .api.auth import auth_bp
    from .api.products import product_bp
    from .api.sales import sales_bp
    from .api.dashboard import dashboard_bp
    from .api.inventory import inventory_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(product_bp, url_prefix='/api/products')
    app.register_blueprint(sales_bp, url_prefix='/api/sales')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(inventory_bp, url_prefix='/api/inventory')

    # 초기 관리자 생성 명령어 등록 (필수)
    from .commands import create_admin_command
    app.cli.add_command(create_admin_command)

    return app