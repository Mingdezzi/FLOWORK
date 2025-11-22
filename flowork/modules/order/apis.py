from flask import request, jsonify
from flask_login import login_required, current_user
from flowork.modules.order import order_bp
from flowork.modules.order.services import update_order_status_simple, create_store_request, process_store_request_status
from flowork.models import StoreOrder, StoreReturn

@order_bp.route('/api/update_order_status', methods=['POST'])
@login_required
def api_update_status():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    oid = request.json.get('order_id')
    stat = request.json.get('new_status')
    if not oid or not stat: return jsonify({'status':'error'}), 400
    
    ok, msg = update_order_status_simple(oid, current_user.store_id, stat)
    if ok: return jsonify({'status':'success'})
    return jsonify({'status':'error', 'message':msg}), 500

@order_bp.route('/api/store_orders', methods=['POST'])
@login_required
def api_create_store_order():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    d = request.json
    ok, msg = create_store_request(StoreOrder, current_user.store_id, d.get('variant_id'), int(d.get('quantity',0)), d.get('date'))
    if ok: return jsonify({'status':'success'})
    return jsonify({'status':'error', 'message':msg}), 500

@order_bp.route('/api/store_returns', methods=['POST'])
@login_required
def api_create_store_return():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    d = request.json
    ok, msg = create_store_request(StoreReturn, current_user.store_id, d.get('variant_id'), int(d.get('quantity',0)), d.get('date'))
    if ok: return jsonify({'status':'success'})
    return jsonify({'status':'error', 'message':msg}), 500

@order_bp.route('/api/store_orders/<int:oid>/status', methods=['POST'])
@login_required
def api_store_order_status(oid):
    if current_user.store_id: return jsonify({'status':'error'}), 403
    d = request.json
    ok, msg = process_store_request_status(StoreOrder, oid, d.get('status'), int(d.get('confirmed_quantity',0)), current_user.id)
    if ok: return jsonify({'status':'success'})
    return jsonify({'status':'error', 'message':msg}), 500

@order_bp.route('/api/store_returns/<int:rid>/status', methods=['POST'])
@login_required
def api_store_return_status(rid):
    if current_user.store_id: return jsonify({'status':'error'}), 403
    d = request.json
    ok, msg = process_store_request_status(StoreReturn, rid, d.get('status'), int(d.get('confirmed_quantity',0)), current_user.id)
    if ok: return jsonify({'status':'success'})
    return jsonify({'status':'error', 'message':msg}), 500