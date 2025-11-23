from flask import render_template, request, abort
from flask_login import login_required, current_user
from flowork.models import db, Customer, Repair
from . import ui_bp

@ui_bp.route('/customer/list')
@login_required
def customer_list():
    if not current_user.store_id:
        abort(403, description="매장 계정 전용입니다.")
    return render_template('customer_list.html', active_page='customer_list')

@ui_bp.route('/repair/list')
@login_required
def repair_list():
    if not current_user.store_id:
        abort(403, description="매장 계정 전용입니다.")
        
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '').strip()
    
    base_query = Repair.query.join(Customer).filter(Repair.store_id == current_user.store_id)
    
    if query:
        base_query = base_query.filter(
            (Customer.name.contains(query)) | (Customer.phone.contains(query)) | (Repair.product_code.contains(query))
        )
        
    pagination = base_query.order_by(Repair.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    
    # 상태 목록 정의
    STATUS_LIST = ["접수", "본사입고", "수선처리", "처리완료", "매장입고", "고객회수", "회수거부", "재접수", "기타"]
    
    return render_template(
        'repair_list.html', 
        active_page='repair_list', 
        repairs=pagination.items, 
        pagination=pagination,
        status_list=STATUS_LIST,
        query=query
    )