from flask import Blueprint

online_bp = Blueprint('online', __name__)

from . import views