from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from flowork.modules.order import order_bp
from flowork.modules.order.services import get_customer_orders, get_order_detail, create_customer_order, update_customer_order, delete_customer_order, get_store_orders_list, get_store_returns_list, generate_sms_link
from flowork.models import Setting, Brand, Store
from flowork.constants import OrderStatus

def _get_brand_name(brand_id):
    s = Setting.query.filter_by(brand_id=brand_id, key='BRAND_NAME').first()
    if s and s.value: return s.value
    b = Brand.query.get(brand_id)
    return b.brand_name if b else "FLOWORK"

def _get_sources(brand_id, my_store_id):
    q = Store.query.filter(Store.brand_id==brand_id, Store.is_active==True)
    if my_store_id: q = q.filter(Store.id != my_store_id)
    stores = q.order_by(Store.store_name).all()
    return stores

@order_bp.route('/orders')
@login_required
def order_list_view():
    if not current_user.store_id: abort(403)
    today = datetime.now()
    yr = request.args.get('year', today.year, type=int)
    mo = request.args.get('month', today.month, type=int)
    
    pending, monthly = get_customer_orders(current_user.store_id, yr, mo)
    bname = _get_brand_name(current_user.current_brand_id)
    
    for o in pending: o.sms_link = generate_sms_link(o, bname)
    for o in monthly: o.sms_link = generate_sms_link(o, bname)
    
    return render_template('order.html', active_page='order', pending_orders=pending, monthly_orders=monthly,
                           year_list=range(today.year, today.year-3, -1), month_list=range(1,13),
                           selected_year=yr, selected_month=mo, PENDING_STATUSES=OrderStatus.PENDING)

@order_bp.route('/order/new', methods=['GET', 'POST'])
@login_required
def new_order_view():
    if not current_user.store_id: abort(403)
    if request.method == 'POST':
        data = request.form.to_dict()
        data['brand_id'] = current_user.current_brand_id
        data['processing_source'] = request.form.getlist('processing_source')
        data['processing_result'] = request.form.getlist('processing_result')
        
        ok, res = create_customer_order(current_user.store_id, data)
        if ok:
            flash(f"주문 등록 완료: {res.customer_name}", "success")
            return redirect(url_for('order.order_list_view'))
        flash(f"오류: {res}", "error")
        
    return render_template('order_detail.html', active_page='order', order=None,
                           order_sources=_get_sources(current_user.current_brand_id, current_user.store_id),
                           order_statuses=OrderStatus.ALL, default_created_at=datetime.now(), form_data=None)

@order_bp.route('/order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def order_detail_view(order_id):
    if not current_user.store_id: abort(403)
    order = get_order_detail(order_id, current_user.store_id)
    if not order: abort(404)
    
    if request.method == 'POST':
        data = request.form.to_dict()
        data['brand_id'] = current_user.current_brand_id
        data['processing_source'] = request.form.getlist('processing_source')
        data['processing_result'] = request.form.getlist('processing_result')
        
        ok, msg = update_customer_order(order_id, current_user.store_id, data)
        if ok:
            flash("수정되었습니다.", "success")
            return redirect(url_for('order.order_detail_view', order_id=order_id))
        flash(f"오류: {msg}", "error")
        
    return render_template('order_detail.html', active_page='order', order=order,
                           order_sources=_get_sources(current_user.current_brand_id, current_user.store_id),
                           order_statuses=OrderStatus.ALL, form_data=None)

@order_bp.route('/order/delete/<int:order_id>', methods=['POST'])
@login_required
def delete_order_view(order_id):
    if not current_user.store_id: abort(403)
    ok, msg = delete_customer_order(order_id, current_user.store_id)
    if ok: flash(f"삭제됨: {msg}", "success")
    else: flash(f"삭제 실패: {msg}", "error")
    return redirect(url_for('order.order_list_view'))

@order_bp.route('/store/orders')
@login_required
def store_order_list_view():
    pg = request.args.get('page', 1, type=int)
    sid = current_user.store_id if current_user.store_id else None
    pagination = get_store_orders_list(current_user.current_brand_id, sid, pg)
    return render_template('store_order_list.html', active_page='store_orders', pagination=pagination)

@order_bp.route('/store/returns')
@login_required
def store_return_list_view():
    pg = request.args.get('page', 1, type=int)
    sid = current_user.store_id if current_user.store_id else None
    pagination = get_store_returns_list(current_user.current_brand_id, sid, pg)
    return render_template('store_return_list.html', active_page='store_returns', pagination=pagination)