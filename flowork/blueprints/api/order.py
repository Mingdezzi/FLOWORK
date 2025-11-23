import traceback
from flask import request, jsonify
from flask_login import login_required, current_user
from flowork.models import db, Order
from . import api_bp

@api_bp.route('/api/update_order_status', methods=['POST'])
@login_required
def api_update_order_status():
    if not current_user.store_id:
        abort(403, description="주문 상태 변경은 매장 계정만 사용할 수 있습니다.")

    data = request.json
    order_id = data.get('order_id')
    new_status = data.get('new_status')

    if not order_id or not new_status:
        return jsonify({'status': 'error', 'message': '필수 정보 누락'}), 400
    
    try:
        order = Order.query.filter_by(
            id=order_id, 
            store_id=current_user.store_id
        ).first()
        
        if not order:
            return jsonify({'status': 'error', 'message': '주문을 찾을 수 없거나 권한이 없습니다.'}), 404
        
        order.order_status = new_status
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': f'주문(ID: {order_id}) 상태가 {new_status}(으)로 변경되었습니다.'})

    except Exception as e:
        db.session.rollback()
        print(f"Error updating order status: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500