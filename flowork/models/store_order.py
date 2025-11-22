from datetime import datetime, date
from ..extensions import db
from sqlalchemy import Index

class StoreOrder(db.Model):
    __tablename__ = 'store_orders'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False)
    order_date = db.Column(db.Date, nullable=False, default=date.today)
    quantity = db.Column(db.Integer, nullable=False) 
    confirmed_quantity = db.Column(db.Integer, nullable=True) 
    status = db.Column(db.String(20), default='REQUESTED', nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.now)
    store = db.relationship('Store', backref='store_orders')
    variant = db.relationship('Variant')
    __table_args__ = (Index('ix_store_order_store_status', 'store_id', 'status'),)

class StoreReturn(db.Model):
    __tablename__ = 'store_returns'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False)
    return_date = db.Column(db.Date, nullable=False, default=date.today)
    quantity = db.Column(db.Integer, nullable=False) 
    confirmed_quantity = db.Column(db.Integer, nullable=True) 
    status = db.Column(db.String(20), default='REQUESTED', nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.now)
    store = db.relationship('Store', backref='store_returns')
    variant = db.relationship('Variant')
    __table_args__ = (Index('ix_store_return_store_status', 'store_id', 'status'),)