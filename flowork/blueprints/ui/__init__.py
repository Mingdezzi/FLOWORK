from flask import Blueprint

ui_bp = Blueprint('ui', __name__, template_folder='../../templates')

from . import main, product, order, sales, admin, errors, processors, stock_transfer, crm, operations, network, store_order, online