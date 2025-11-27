from flask import Blueprint, request, jsonify
from backend.models import db, PosOrder, PosOrderItem, Stock, User, Variant
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('', methods=['POST'])
@jwt_required()
def create_sale():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user.store_id:
        return jsonify({'message': 'Store account required'}), 403

    data = request.json
    items = data.get('items', []) # [{variant_id, quantity, price}, ...]
    
    if not items:
        return jsonify({'message': 'No items'}), 400

    try:
        # 영수증 번호 생성 (날짜 + 난수 또는 시퀀스)
        order_num = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{user.store_id}"
        
        total_amount = 0
        new_order = PosOrder(
            store_id=user.store_id,
            user_id=user.id,
            order_number=order_num,
            payment_method=data.get('payment_method', 'CARD')
        )
        db.session.add(new_order)
        db.session.flush() # ID 생성

        for item in items:
            v_id = item['variant_id']
            qty = item['quantity']
            price = item['price'] # 할인이 적용된 실제 판매가
            
            # 재고 차감
            stock = Stock.query.filter_by(store_id=user.store_id, variant_id=v_id).with_for_update().first()
            if not stock or stock.quantity < qty:
                raise Exception(f"Insufficient stock for variant {v_id}")
            
            stock.quantity -= qty
            
            # 상품 정보 스냅샷
            variant = Variant.query.get(v_id)
            
            order_item = PosOrderItem(
                order_id=new_order.id,
                variant_id=v_id,
                product_name_snapshot=variant.product.name,
                quantity=qty,
                unit_price=price,
                subtotal=price * qty
            )
            db.session.add(order_item)
            total_amount += (price * qty)
        
        new_order.total_amount = total_amount
        db.session.commit()
        
        return jsonify({'status': 'success', 'order_number': order_num})

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500