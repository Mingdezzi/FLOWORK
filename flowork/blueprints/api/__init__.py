from flask import Blueprint

api_bp = Blueprint('api', __name__)

from . import inventory, sales, order, schedule, admin, tasks, maintenance, stock_transfer, crm, operations, network, store_order, product_image, system