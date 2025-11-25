from flask import request, jsonify, abort
from flask_login import login_required, current_user
from flowork.services.transfer_service import TransferService
from . import api_bp

@api_bp.route('/api/stock_transfer/request', methods=['POST'])
@login_required
def request_transfer():
    """매장 요청 (B매장이 A매장에 요청)"""
    if not current_user.store_id:
        return jsonify({'status': 'error', 'message': '매장 계정만 요청할 수 있습니다.'}), 403

    data = request.json
    
    result = TransferService.request_transfer(
        source_store_id=data.get('source_store_id'),
        target_store_id=current_user.store_id,
        variant_id=data.get('variant_id'),
        quantity=int(data.get('quantity', 0))
    )
    
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code

@api_bp.route('/api/stock_transfer/instruct', methods=['POST'])
@login_required
def instruct_transfer():
    """본사 지시 (본사가 A->B 이동 지시)"""
    if current_user.store_id:
        return jsonify({'status': 'error', 'message': '본사 관리자만 지시할 수 있습니다.'}), 403

    data = request.json
    
    result = TransferService.instruct_transfer(
        source_store_id=data.get('source_store_id'),
        target_store_id=data.get('target_store_id'),
        variant_id=data.get('variant_id'),
        quantity=int(data.get('quantity', 0))
    )
    
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code

@api_bp.route('/api/stock_transfer/<int:t_id>/ship', methods=['POST'])
@login_required
def ship_transfer(t_id):
    """이동등록 (출고확정)"""
    result = TransferService.ship_transfer(t_id, current_user.store_id, current_user.id)
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code

@api_bp.route('/api/stock_transfer/<int:t_id>/receive', methods=['POST'])
@login_required
def receive_transfer(t_id):
    """입고확정"""
    result = TransferService.receive_transfer(t_id, current_user.store_id, current_user.id)
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code

@api_bp.route('/api/stock_transfer/<int:t_id>/reject', methods=['POST'])
@login_required
def reject_transfer(t_id):
    """출고거부"""
    result = TransferService.reject_transfer(t_id, current_user.store_id)
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code