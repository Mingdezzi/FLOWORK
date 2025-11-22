from flowork.models import db, StockTransfer, StoreStock, StockHistory, Store, Variant
from sqlalchemy import or_

def get_outbound_transfers(store_id):
    return StockTransfer.query.filter_by(source_store_id=store_id).order_by(StockTransfer.created_at.desc()).all()

def get_inbound_transfers(store_id):
    return StockTransfer.query.filter_by(target_store_id=store_id).order_by(StockTransfer.created_at.desc()).all()

def get_all_transfers(brand_id, store_id=None):
    q = StockTransfer.query.join(StockTransfer.source_store).filter(Store.brand_id == brand_id)
    if store_id:
        q = q.filter(or_(StockTransfer.source_store_id == store_id, StockTransfer.target_store_id == store_id))
    return q.order_by(StockTransfer.created_at.desc()).limit(100).all()

def request_transfer_service(source_id, target_id, variant_id, qty):
    try:
        t = StockTransfer(
            transfer_type='REQUEST', status='REQUESTED',
            source_store_id=source_id, target_store_id=target_id,
            variant_id=variant_id, quantity=qty
        )
        db.session.add(t)
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def process_transfer_ship(t_id, store_id, user_id):
    try:
        t = db.session.get(StockTransfer, t_id)
        if not t or t.source_store_id != store_id: return False, "권한 없음"
        if t.status != 'REQUESTED': return False, "처리 불가 상태"
        
        stk = StoreStock.query.filter_by(store_id=store_id, variant_id=t.variant_id).with_for_update().first()
        if not stk or stk.quantity < t.quantity: return False, "재고 부족"
        
        stk.quantity -= t.quantity
        h = StockHistory(store_id=store_id, variant_id=t.variant_id, user_id=user_id, change_type='TRANSFER_OUT', quantity_change=-t.quantity, current_quantity=stk.quantity)
        db.session.add(h)
        
        t.status = 'SHIPPED'
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def process_transfer_receive(t_id, store_id, user_id):
    try:
        t = db.session.get(StockTransfer, t_id)
        if not t or t.target_store_id != store_id: return False, "권한 없음"
        if t.status != 'SHIPPED': return False, "처리 불가 상태"
        
        stk = StoreStock.query.filter_by(store_id=store_id, variant_id=t.variant_id).with_for_update().first()
        if not stk:
            stk = StoreStock(store_id=store_id, variant_id=t.variant_id, quantity=0)
            db.session.add(stk)
            
        stk.quantity += t.quantity
        h = StockHistory(store_id=store_id, variant_id=t.variant_id, user_id=user_id, change_type='TRANSFER_IN', quantity_change=t.quantity, current_quantity=stk.quantity)
        db.session.add(h)
        
        t.status = 'RECEIVED'
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def process_transfer_reject(t_id, store_id):
    try:
        t = db.session.get(StockTransfer, t_id)
        if not t or t.source_store_id != store_id: return False, "권한 없음"
        if t.status != 'REQUESTED': return False, "처리 불가 상태"
        t.status = 'REJECTED'
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)