import traceback
from datetime import datetime, date
from flowork.extensions import db
from flowork.models import StoreOrder, StoreReturn, StoreStock, StockHistory, Variant
from flowork.constants import TransferStatus, StockChangeType

class StoreOrderService:
    @staticmethod
    def create_order(store_id, variant_id, quantity, order_date_str):
        try:
            if quantity <= 0: 
                return {'status': 'error', 'message': '수량은 1개 이상이어야 합니다.'}
            
            order_date = datetime.strptime(order_date_str, '%Y-%m-%d').date() if order_date_str else date.today()
            
            order = StoreOrder(
                store_id=store_id,
                variant_id=variant_id,
                order_date=order_date,
                quantity=quantity,
                status=TransferStatus.REQUESTED
            )
            db.session.add(order)
            db.session.commit()
            return {'status': 'success', 'message': '주문이 요청되었습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def update_order_status(order_id, status, confirmed_qty, user_id):
        try:
            order = db.session.get(StoreOrder, order_id)
            if not order: return {'status': 'error', 'message': '주문 내역 없음'}
            if order.status != TransferStatus.REQUESTED: 
                return {'status': 'error', 'message': '이미 처리된 주문입니다.'}
            
            if status == 'APPROVED': # TransferStatus.RECEIVED (개념상 승인이므로 매핑 필요할 수도 있으나 여기선 APPROVED 사용)
                if confirmed_qty <= 0: 
                    return {'status': 'error', 'message': '확정 수량 오류'}
                
                # 1. 본사 재고 차감
                variant = db.session.get(Variant, order.variant_id)
                variant.hq_quantity -= confirmed_qty
                
                # 2. 매장 재고 증가
                stock = StoreStock.query.filter_by(store_id=order.store_id, variant_id=order.variant_id).first()
                if not stock:
                    stock = StoreStock(store_id=order.store_id, variant_id=order.variant_id, quantity=0)
                    db.session.add(stock)
                stock.quantity += confirmed_qty
                
                # 3. 이력 (매장 기준 입고)
                history = StockHistory(
                    store_id=order.store_id,
                    variant_id=order.variant_id,
                    user_id=user_id,
                    change_type=StockChangeType.ORDER_IN,
                    quantity_change=confirmed_qty,
                    current_quantity=stock.quantity
                )
                db.session.add(history)
                
                order.confirmed_quantity = confirmed_qty
                order.status = 'APPROVED'
                
            elif status == 'REJECTED':
                order.status = 'REJECTED'
                
            db.session.commit()
            return {'status': 'success', 'message': '처리되었습니다.'}
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def create_return(store_id, variant_id, quantity, return_date_str):
        try:
            if quantity <= 0: return {'status': 'error', 'message': '수량 오류'}
            
            return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date() if return_date_str else date.today()
            
            ret = StoreReturn(
                store_id=store_id,
                variant_id=variant_id,
                return_date=return_date,
                quantity=quantity,
                status=TransferStatus.REQUESTED
            )
            db.session.add(ret)
            db.session.commit()
            return {'status': 'success', 'message': '반품이 요청되었습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def update_return_status(return_id, status, confirmed_qty, user_id):
        try:
            ret = db.session.get(StoreReturn, return_id)
            if not ret: return {'status': 'error', 'message': '내역 없음'}
            if ret.status != TransferStatus.REQUESTED: 
                return {'status': 'error', 'message': '이미 처리됨'}
            
            if status == 'APPROVED':
                if confirmed_qty <= 0: return {'status': 'error', 'message': '수량 오류'}
                
                # 1. 매장 재고 차감
                stock = StoreStock.query.filter_by(store_id=ret.store_id, variant_id=ret.variant_id).first()
                if stock:
                    stock.quantity -= confirmed_qty
                    
                    history = StockHistory(
                        store_id=ret.store_id,
                        variant_id=ret.variant_id,
                        user_id=user_id,
                        change_type=StockChangeType.RETURN_OUT,
                        quantity_change=-confirmed_qty,
                        current_quantity=stock.quantity
                    )
                    db.session.add(history)
                
                # 2. 본사 재고 증가
                variant = db.session.get(Variant, ret.variant_id)
                variant.hq_quantity += confirmed_qty
                
                ret.confirmed_quantity = confirmed_qty
                ret.status = 'APPROVED'
                
            elif status == 'REJECTED':
                ret.status = 'REJECTED'
                
            db.session.commit()
            return {'status': 'success', 'message': '처리되었습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}