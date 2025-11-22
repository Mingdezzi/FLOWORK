from flask import render_template, request, abort
from flask_login import login_required, current_user
from flowork.modules.crm import crm_bp
from flowork.models import Repair, Customer

@crm_bp.route('/customer/list')
@login_required
def customer_list_view():
    if not current_user.store_id: abort(403)
    return render_template('customer_list.html', active_page='customer_list')

@crm_bp.route('/repair/list')
@login_required
def repair_list_view():
    if not current_user.store_id: abort(403)
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '').strip()
    
    q = Repair.query.join(Customer).filter(Repair.store_id == current_user.store_id)
    if query:
        q = q.filter((Customer.name.contains(query)) | (Customer.phone.contains(query)) | (Repair.product_code.contains(query)))
        
    pagination = q.order_by(Repair.created_at.desc()).paginate(page=page, per_page=15)
    status_list = ["접수", "본사입고", "수선처리", "처리완료", "매장입고", "고객회수", "회수거부", "재접수", "기타"]
    
    return render_template('repair_list.html', active_page='repair_list', repairs=pagination.items, pagination=pagination, status_list=status_list, query=query)