from datetime import datetime
from ..extensions import db
from sqlalchemy import Index

class StockTransfer(db.Model):
    __tablename__ = 'stock_transfers'
    id = db.Column(db.Integer, primary_key=True)
    transfer_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='REQUESTED', nullable=False)
    source_store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    target_store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.now)
    source_store = db.relationship('Store', foreign_keys=[source_store_id], backref='transfers_sent')
    target_store = db.relationship('Store', foreign_keys=[target_store_id], backref='transfers_received')
    variant = db.relationship('Variant')
    __table_args__ = (
        Index('ix_transfer_source_status', 'source_store_id', 'status'),
        Index('ix_transfer_target_status', 'target_store_id', 'status'),
    )