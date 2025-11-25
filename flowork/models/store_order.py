from datetime import datetime, date
from ..extensions import db
from sqlalchemy import Index

class StoreOrder(db.Model):
    """매장 -> 본사 상품 주문 (발주)"""
    __tablename__ = 'store_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False)
    
    order_date = db.Column(db.Date, nullable=False, default=date.today)
    quantity = db.Column(db.Integer, nullable=False) # 주문 수량
    confirmed_quantity = db.Column(db.Integer, nullable=True) # 확정 수량 (본사 승인 시 변경 가능)
    
    # 상태: REQUESTED(요청), APPROVED(승인/출고), REJECTED(거절)
    status = db.Column(db.String(20), default='REQUESTED', nullable=False)
    note = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.now)
    
    # [수정] backref 이름을 'orders' -> 'store_orders'로 변경 (충돌 방지)
    store = db.relationship('Store', backref='store_orders')
    variant = db.relationship('Variant')

    __table_args__ = (
        Index('ix_store_order_store_status', 'store_id', 'status'),
    )

class StoreReturn(db.Model):
    """매장 -> 본사 상품 반품"""
    __tablename__ = 'store_returns'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False)
    
    return_date = db.Column(db.Date, nullable=False, default=date.today)
    quantity = db.Column(db.Integer, nullable=False) # 반품 요청 수량
    confirmed_quantity = db.Column(db.Integer, nullable=True) # 확정 수량
    
    # 상태: REQUESTED(요청), APPROVED(승인/입고), REJECTED(거절)
    status = db.Column(db.String(20), default='REQUESTED', nullable=False)
    note = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.now)
    
    # [수정] backref 이름을 'returns' -> 'store_returns'로 변경 (명확성 및 충돌 방지)
    store = db.relationship('Store', backref='store_returns')
    variant = db.relationship('Variant')

    __table_args__ = (
        Index('ix_store_return_store_status', 'store_id', 'status'),
    )
