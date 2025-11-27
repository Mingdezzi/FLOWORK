from flask import Blueprint, request

ui_bp = Blueprint('ui', __name__, template_folder='../../templates')

# [수정] Context Processor 도입: 모든 템플릿 렌더링 시 자동으로 호출됨
@ui_bp.context_processor
def inject_spa_context():
    """
    모든 UI 템플릿 렌더링 시 호출되어,
    AJAX 요청 여부에 따라 상속받을 부모 템플릿(extends_template)을 결정해 주입합니다.
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # 탭(TabManager)에서 호출한 경우: 껍데기 없는 템플릿 사용
        return dict(extends_template='base_ajax.html')
    else:
        # 브라우저 직접 접속인 경우: 전체 레이아웃 템플릿 사용
        return dict(extends_template='base.html')

# 하위 뷰 모듈 임포트 (순서 중요)
from . import main, product, order, sales, admin, errors, processors, stock_transfer, crm, operations, network, store_order, online