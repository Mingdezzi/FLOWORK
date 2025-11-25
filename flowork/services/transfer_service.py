import traceback
from flowork.extensions import db
from flowork.models import StockTransfer, StoreStock, StockHistory
from flowork.constants import TransferType, TransferStatus, StockChangeType

class TransferService:
    @staticmethod
    def request_transfer(source_store_id, target_store_id, variant_id, quantity):
        try:
            if quantity <= 0:
                return {'status': 'error', 'message': '수량은 1개 이상이어야 합니다.'}

            transfer = StockTransfer(
                transfer_type=TransferType.REQUEST,
                status=TransferStatus.REQUESTED,
                source_store_id=source_store_id,
                target_store_id=target_store_id,
                variant_id=variant_id,
                quantity=quantity
            )
            db.session.add(transfer)
            db.session.commit()
            return {'status': 'success', 'message': '재고 이동 요청이 등록되었습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def instruct_transfer(source_store_id, target_store_id, variant_id, quantity):
        try:
            if quantity <= 0:
                return {'status': 'error', 'message': '수량 오류'}

            transfer = StockTransfer(
                transfer_type=TransferType.INSTRUCTION,
                status=TransferStatus.REQUESTED,
                source_store_id=source_store_id,
                target_store_id=target_store_id,
                variant_id=variant_id,
                quantity=quantity
            )
            db.session.add(transfer)
            db.session.commit()
            return {'status': 'success', 'message': '이동 지시가 등록되었습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def ship_transfer(transfer_id, user_store_id, user_id):
        """출고 확정 (보내는 매장 재고 차감)"""
        try:
            transfer = db.session.get(StockTransfer, transfer_id)
            if not transfer: return {'status': 'error', 'message': '내역 없음'}
            
            if transfer.source_store_id != user_store_id:
                return {'status': 'error', 'message': '보내는 매장만 출고 처리할 수 있습니다.'}
                
            if transfer.status != TransferStatus.REQUESTED:
                return {'status': 'error', 'message': '처리할 수 없는 상태입니다.'}

            # 재고 차감
            stock = StoreStock.query.filter_by(
                store_id=transfer.source_store_id, 
                variant_id=transfer.variant_id
            ).with_for_update().first()
            
            if not stock or stock.quantity < transfer.quantity:
                return {'status': 'error', 'message': '재고가 부족합니다.'}
                
            stock.quantity -= transfer.quantity
            
            # 이력 기록
            history = StockHistory(
                store_id=transfer.source_store_id,
                variant_id=transfer.variant_id,
                user_id=user_id,
                change_type=StockChangeType.TRANSFER_OUT,
                quantity_change=-transfer.quantity,
                current_quantity=stock.quantity
            )
            db.session.add(history)
            
            transfer.status = TransferStatus.SHIPPED
            db.session.commit()
            return {'status': 'success', 'message': '출고(이동등록) 처리되었습니다.'}
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def receive_transfer(transfer_id, user_store_id, user_id):
        """입고 확정 (받는 매장 재고 증가)"""
        try:
            transfer = db.session.get(StockTransfer, transfer_id)
            if not transfer: return {'status': 'error', 'message': '내역 없음'}
            
            if transfer.target_store_id != user_store_id:
                return {'status': 'error', 'message': '받는 매장만 입고 처리할 수 있습니다.'}
                
            if transfer.status != TransferStatus.SHIPPED:
                return {'status': 'error', 'message': '아직 출고되지 않았거나 이미 처리된 건입니다.'}

            # 재고 증가 (없으면 생성)
            stock = StoreStock.query.filter_by(
                store_id=transfer.target_store_id, 
                variant_id=transfer.variant_id
            ).with_for_update().first()
            
            if not stock:
                stock = StoreStock(store_id=transfer.target_store_id, variant_id=transfer.variant_id, quantity=0)
                db.session.add(stock)
                
            stock.quantity += transfer.quantity
            
            history = StockHistory(
                store_id=transfer.target_store_id,
                variant_id=transfer.variant_id,
                user_id=user_id,
                change_type=StockChangeType.TRANSFER_IN,
                quantity_change=transfer.quantity,
                current_quantity=stock.quantity
            )
            db.session.add(history)
            
            transfer.status = TransferStatus.RECEIVED
            db.session.commit()
            return {'status': 'success', 'message': '입고 확정되었습니다.'}
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def reject_transfer(transfer_id, user_store_id):
        """출고 거부"""
        try:
            transfer = db.session.get(StockTransfer, transfer_id)
            if not transfer: return {'status': 'error', 'message': '내역 없음'}
            
            if transfer.source_store_id != user_store_id:
                return {'status': 'error', 'message': '권한이 없습니다.'}
                
            if transfer.status != TransferStatus.REQUESTED:
                return {'status': 'error', 'message': '거부할 수 없는 상태입니다.'}
                
            transfer.status = TransferStatus.REJECTED
            db.session.commit()
            return {'status': 'success', 'message': '요청을 거부했습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}