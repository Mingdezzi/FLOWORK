from flask import Blueprint
crm_bp = Blueprint('crm', __name__)
from . import views, apis