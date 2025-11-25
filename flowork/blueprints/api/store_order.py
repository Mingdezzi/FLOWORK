from flask import request, jsonify
from flask_login import login_required, current_user
from flowork.services.store_order_service import StoreOrderService
from . import api_bp

# --- 매장 주문 (Store Order) API ---

@api_bp.route('/api/store_orders', methods=['POST'])
@login_required
def create_store_order():
    """매장: 본사에 주문 요청"""
    if not current_user.store_id:
        return jsonify({'status': 'error', 'message': '매장 계정만 가능합니다.'}), 403
        
    data = request.json
    
    result = StoreOrderService.create_order(
        store_id=current_user.store_id,
        variant_id=data.get('variant_id'),
        quantity=int(data.get('quantity', 0)),
        order_date_str=data.get('date')
    )
    
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code

@api_bp.route('/api/store_orders/<int:oid>/status', methods=['POST'])
@login_required
def update_store_order_status(oid):
    """본사: 주문 승인(출고) 또는 거절"""
    if current_user.store_id: 
        return jsonify({'status': 'error', 'message': '본사 관리자만 가능합니다.'}), 403
    
    data = request.json
    result = StoreOrderService.update_order_status(
        order_id=oid,
        status=data.get('status'),
        confirmed_qty=int(data.get('confirmed_quantity', 0)),
        user_id=current_user.id
    )
    
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code


# --- 매장 반품 (Store Return) API ---

@api_bp.route('/api/store_returns', methods=['POST'])
@login_required
def create_store_return():
    """매장: 본사에 반품 요청"""
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
        
    data = request.json
    
    result = StoreOrderService.create_return(
        store_id=current_user.store_id,
        variant_id=data.get('variant_id'),
        quantity=int(data.get('quantity', 0)),
        return_date_str=data.get('date')
    )
    
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code

@api_bp.route('/api/store_returns/<int:rid>/status', methods=['POST'])
@login_required
def update_store_return_status(rid):
    """본사: 반품 승인(입고) 또는 거절"""
    if current_user.store_id: return jsonify({'status': 'error'}), 403
    
    data = request.json
    result = StoreOrderService.update_return_status(
        return_id=rid,
        status=data.get('status'),
        confirmed_qty=int(data.get('confirmed_quantity', 0)),
        user_id=current_user.id
    )
    
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code