from flask import render_template, abort
from flask_login import login_required, current_user
from flowork.modules.stock_transfer import stock_transfer_bp
from flowork.modules.stock_transfer.services import get_outbound_transfers, get_inbound_transfers, get_all_transfers
from flowork.models import Store

@stock_transfer_bp.route('/stock_transfer/out')
@login_required
def stock_transfer_out_view():
    if not current_user.store_id: abort(403)
    return render_template('stock_transfer_out.html', active_page='transfer_out', transfers=get_outbound_transfers(current_user.store_id))

@stock_transfer_bp.route('/stock_transfer/in')
@login_required
def stock_transfer_in_view():
    if not current_user.store_id: abort(403)
    others = Store.query.filter(Store.brand_id==current_user.current_brand_id, Store.id!=current_user.store_id, Store.is_active==True).all()
    return render_template('stock_transfer_in.html', active_page='transfer_in', transfers=get_inbound_transfers(current_user.store_id), stores=others)

@stock_transfer_bp.route('/stock_transfer/status')
@login_required
def stock_transfer_status_view():
    return render_template('stock_transfer_status.html', active_page='transfer_status', transfers=get_all_transfers(current_user.current_brand_id, current_user.store_id))