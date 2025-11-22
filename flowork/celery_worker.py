from flowork import create_app
from flowork.extensions import celery
from config import Config

app = create_app(Config)
app.app_context().push()