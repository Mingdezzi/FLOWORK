from flask import Blueprint

stock_transfer_bp = Blueprint('stock_transfer', __name__)

from . import views, apis