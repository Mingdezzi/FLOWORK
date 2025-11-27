from flask import Blueprint

api_bp = Blueprint('api', __name__)

# API 모듈 등록 (하위 뷰의 라우트들이 등록됨)
from . import (
    inventory, 
    sales, 
    order, 
    schedule, 
    admin, 
    tasks, 
    maintenance, 
    stock_transfer, 
    crm, 
    operations, 
    network, 
    store_order, 
    product_image,
    dashboard  # [신규] 대시보드 SPA용 API 추가
)