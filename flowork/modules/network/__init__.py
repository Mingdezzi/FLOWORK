from flask import Blueprint

network_bp = Blueprint('network', __name__)

from . import views, apis