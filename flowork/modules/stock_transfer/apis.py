from flask import request, jsonify
from flask_login import login_required, current_user
from flowork.modules.stock_transfer import stock_transfer_bp
from flowork.modules.stock_transfer.services import request_transfer_service, process_transfer_ship, process_transfer_receive, process_transfer_reject

@stock_transfer_bp.route('/api/stock_transfer/request', methods=['POST'])
@login_required
def api_request_transfer():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    d = request.json
    ok, msg = request_transfer_service(d.get('source_store_id'), current_user.store_id, d.get('variant_id'), int(d.get('quantity', 0)))
    if ok: return jsonify({'status':'success', 'message':'요청 완료'})
    return jsonify({'status':'error', 'message':msg}), 500

@stock_transfer_bp.route('/api/stock_transfer/<int:tid>/ship', methods=['POST'])
@login_required
def api_ship_transfer(tid):
    ok, msg = process_transfer_ship(tid, current_user.store_id, current_user.id)
    if ok: return jsonify({'status':'success', 'message':'출고 완료'})
    return jsonify({'status':'error', 'message':msg}), 500

@stock_transfer_bp.route('/api/stock_transfer/<int:tid>/receive', methods=['POST'])
@login_required
def api_receive_transfer(tid):
    ok, msg = process_transfer_receive(tid, current_user.store_id, current_user.id)
    if ok: return jsonify({'status':'success', 'message':'입고 완료'})
    return jsonify({'status':'error', 'message':msg}), 500

@stock_transfer_bp.route('/api/stock_transfer/<int:tid>/reject', methods=['POST'])
@login_required
def api_reject_transfer(tid):
    ok, msg = process_transfer_reject(tid, current_user.store_id)
    if ok: return jsonify({'status':'success', 'message':'거부 완료'})
    return jsonify({'status':'error', 'message':msg}), 500