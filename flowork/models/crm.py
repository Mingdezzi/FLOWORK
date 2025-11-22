from datetime import datetime
from ..extensions import db
from sqlalchemy import Index

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True)
    address = db.Column(db.String(255), nullable=True)
    customer_code = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    repairs = db.relationship('Repair', backref='customer', lazy='dynamic', cascade="all, delete-orphan")

class Repair(db.Model):
    __tablename__ = 'repairs'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    reception_date = db.Column(db.Date, nullable=False, default=datetime.now)
    product_info = db.Column(db.String(255), nullable=True) 
    product_code = db.Column(db.String(100), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    size = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True) 
    status = db.Column(db.String(20), default='접수', nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.now)
    store = db.relationship('Store', backref='repairs')
    __table_args__ = (Index('ix_repair_store_status', 'store_id', 'status'),)