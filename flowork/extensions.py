from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from celery import Celery

db = SQLAlchemy()
login_manager = LoginManager()
celery = Celery()