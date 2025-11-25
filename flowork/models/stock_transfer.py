from datetime import datetime
from ..extensions import db
from sqlalchemy import Index

class StockTransfer(db.Model):
    __tablename__ = 'stock_transfers'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 이동 유형: 'INSTRUCTION' (본사지시), 'REQUEST' (매장요청)
    transfer_type = db.Column(db.String(20), nullable=False)
    
    # 상태: 
    # - REQUESTED (요청됨/지시됨)
    # - SHIPPED   (이동등록/출고확정 - 보내는 매장 재고 차감됨)
    # - RECEIVED  (입고확정 - 받는 매장 재고 증가됨)
    # - REJECTED  (출고거부)
    # - CANCELLED (취소됨)
    status = db.Column(db.String(20), default='REQUESTED', nullable=False)
    
    source_store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False) # 보내는 매장 (A)
    target_store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False) # 받는 매장 (B)
    
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.now)
    
    # 관계 설정
    source_store = db.relationship('Store', foreign_keys=[source_store_id], backref='transfers_sent')
    target_store = db.relationship('Store', foreign_keys=[target_store_id], backref='transfers_received')
    variant = db.relationship('Variant')

    __table_args__ = (
        Index('ix_transfer_source_status', 'source_store_id', 'status'),
        Index('ix_transfer_target_status', 'target_store_id', 'status'),
    )