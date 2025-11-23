from flask import render_template, request
from flask_login import login_required, current_user
from flowork.models import db, StoreOrder, StoreReturn, Store
from . import ui_bp

@ui_bp.route('/store/orders')
@login_required
def store_order_list():
    page = request.args.get('page', 1, type=int)
    query = StoreOrder.query.join(Store).filter(Store.brand_id == current_user.current_brand_id)
    
    if current_user.store_id:
        query = query.filter(StoreOrder.store_id == current_user.store_id)
        
    pagination = query.order_by(StoreOrder.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('store_order_list.html', active_page='store_orders', pagination=pagination)

@ui_bp.route('/store/returns')
@login_required
def store_return_list():
    page = request.args.get('page', 1, type=int)
    query = StoreReturn.query.join(Store).filter(Store.brand_id == current_user.current_brand_id)
    
    if current_user.store_id:
        query = query.filter(StoreReturn.store_id == current_user.store_id)
        
    pagination = query.order_by(StoreReturn.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('store_return_list.html', active_page='store_returns', pagination=pagination)