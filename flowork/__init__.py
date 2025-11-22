import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from .extensions import db, login_manager, celery
from .models import User
from .commands import init_db_command, update_db_command

csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = '로그인이 필요합니다.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app(config_class):
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config_class)
    
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = config_class.SQLALCHEMY_ENGINE_OPTIONS

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    celery.conf.update(app.config)
    celery.conf.broker_url = app.config['CELERY_BROKER_URL']
    celery.conf.result_backend = app.config['CELERY_RESULT_BACKEND']

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    app.cli.add_command(init_db_command)
    app.cli.add_command(update_db_command)

    from .blueprints.ui import ui_bp
    from .blueprints.api import api_bp
    from .blueprints.auth import auth_bp
    
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    
    return app