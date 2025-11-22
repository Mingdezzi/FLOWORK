from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from celery import Celery

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
cache = Cache()
celery = Celery()