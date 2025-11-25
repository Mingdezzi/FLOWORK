from flask import render_template, request
from . import ui_bp
from ...extensions import db
import traceback

# 엔드포인트(뷰 함수 이름)와 네비게이션 메뉴 ID(active_page) 매핑 테이블
ENDPOINT_MAP = {
    # 영업 관리
    'ui.sales_register': 'sales',
    'ui.sales_record': 'sales_record',
    'ui.sales_detail': 'sales_record',
    'ui.order_list': 'order',
    'ui.new_order': 'order',
    'ui.order_detail': 'order',
    'ui.store_order_list': 'store_orders',
    'ui.store_return_list': 'store_returns',
    'ui.online_management': 'online_mgmt',

    # 재고/물류
    'ui.search_page': 'search',
    'ui.product_detail': 'search',  # 상품 상세도 검색 메뉴의 일부로 봄
    'ui.list_page': 'list',
    'ui.check_page': 'check',
    'ui.stock_transfer_in': 'transfer_in',
    'ui.stock_transfer_out': 'transfer_out',
    'ui.stock_transfer_status': 'transfer_status',
    'ui.stock_overview': 'stock_overview',

    # 매장 운영
    'ui.schedule': 'schedule',
    'ui.attendance_page': 'attendance',
    'ui.competitor_sales_page': 'competitor_sales',
    'ui.customer_list': 'customer_list',
    'ui.repair_list': 'repair_list',
    'ui.announcement_list': 'announcements',
    'ui.announcement_detail': 'announcements',
    'ui.suggestion_list': 'suggestion',
    'ui.suggestion_detail': 'suggestion',
    'ui.mail_box': 'mail',
    'ui.mail_compose': 'mail',
    'ui.mail_detail': 'mail',

    # 시스템 설정
    'ui.stock_management': 'stock',
    'ui.setting_page': 'setting',
    'ui.system_logs': 'system_log', # [신규] 추가
    
    # 홈
    'ui.home': 'home'
}

def get_active_page():
    """
    현재 요청의 엔드포인트를 기반으로 활성화할 메뉴 ID를 반환합니다.
    매핑되지 않은 경우(예: 없는 주소) 'home'을 기본값으로 반환합니다.
    """
    try:
        if request.endpoint in ENDPOINT_MAP:
            return ENDPOINT_MAP[request.endpoint]
        
        # 엔드포인트가 없는 경우(404 등), URL 경로로 추측 (보조 로직)
        path = request.path
        if path.startswith('/sales/'): return 'sales_record'
        if path.startswith('/order'): return 'order'
        if path.startswith('/store/orders'): return 'store_orders'
        if path.startswith('/store/returns'): return 'store_returns'
        if path.startswith('/online'): return 'online_mgmt'
        if path.startswith('/product'): return 'search'
        if path.startswith('/stock/transfer/in'): return 'transfer_in'
        if path.startswith('/stock/transfer/out'): return 'transfer_out'
        
    except Exception:
        pass
    
    return 'home' # 기본값

@ui_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('404.html', 
                           error_description=getattr(error, 'description', '페이지를 찾을 수 없습니다.'),
                           active_page=get_active_page()), 404

@ui_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    print(f"Internal Server Error: {error}")
    traceback.print_exc() 
    return render_template('500.html', 
                           error_message=str(error),
                           active_page=get_active_page()), 500

@ui_bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('403.html',
                           error_description=getattr(error, 'description', '이 작업에 대한 권한이 없습니다.'),
                           active_page=get_active_page()), 403