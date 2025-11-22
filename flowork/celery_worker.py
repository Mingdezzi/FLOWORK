from flowork import create_app, make_celery
from config import Config

app = create_app(Config)
celery = make_celery(app)

from flowork import celery_tasks