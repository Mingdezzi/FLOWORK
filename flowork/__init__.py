import os
from flask import Flask
from .extensions import db, login_manager, csrf, cache, celery
from .models import User
from .commands import init_db_command, update_db_command

login_manager.login_view = 'auth.login_view'
login_manager.login_message = '로그인이 필요합니다.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app(config_class):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)
    
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)

    celery.conf.broker_url = app.config['CELERY_BROKER_URL']
    celery.conf.result_backend = app.config['CELERY_RESULT_BACKEND']
    celery.conf.update(
        accept_content=['json'], task_serializer='json', result_serializer='json',
        timezone=os.environ.get('TZ', 'Asia/Seoul')
    )
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context(): return self.run(*args, **kwargs)
    celery.Task = ContextTask

    app.cli.add_command(init_db_command)
    app.cli.add_command(update_db_command)

    from .modules.main import main_bp
    from .modules.auth import auth_bp
    from .modules.product import product_bp
    from .modules.order import order_bp
    from .modules.sales import sales_bp
    from .modules.admin import admin_bp
    from .modules.network import network_bp
    from .modules.operations import operations_bp
    from .modules.online import online_bp 
    from .modules.crm import crm_bp
    from .modules.stock_transfer import stock_transfer_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(network_bp)
    app.register_blueprint(operations_bp)
    app.register_blueprint(online_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(stock_transfer_bp)

    return app