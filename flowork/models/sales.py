from ..extensions import db
from datetime import datetime
from sqlalchemy import Index
from flowork.constants import SaleStatus, PaymentMethod

class Order(db.Model):
    __tablename__ = 'orders'
    __table_args__ = (
        Index('ix_order_store_status_created', 'store_id', 'order_status', 'created_at'),
        Index('ix_order_created', 'created_at'),
        Index('ix_order_store_created', 'store_id', 'created_at'), 
    )
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='SET NULL'), nullable=True) 
    
    product_number = db.Column(db.String, nullable=False) 
    product_name = db.Column(db.String, nullable=False) 
    color = db.Column(db.String) 
    size = db.Column(db.String) 
    
    customer_name = db.Column(db.String, nullable=False)
    customer_phone = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now) 
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True) 
    
    reception_method = db.Column(db.String(50), nullable=False, default='방문수령') 
    postcode = db.Column(db.String(10))
    address1 = db.Column(db.String(255))
    address2 = db.Column(db.String(255)) 
    
    order_status = db.Column(db.String(50), default='고객주문') 
    remarks = db.Column(db.Text, nullable=True) 
    courier = db.Column(db.String(100), nullable=True)
    tracking_number = db.Column(db.String(100), nullable=True)
    
    processing_steps = db.relationship('OrderProcessing', backref='order', lazy='dynamic', cascade="all, delete-orphan")

class OrderProcessing(db.Model):
    __tablename__ = 'order_processing'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    source_store_id = db.Column(db.Integer, db.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False, index=True)
    source_result = db.Column(db.String(50), nullable=True) 

class Sale(db.Model):
    __tablename__ = 'sales'
    __table_args__ = (
        Index('ix_sales_store_date', 'store_id', 'sale_date'),
    )
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) 
    
    sale_date = db.Column(db.Date, nullable=False)
    daily_number = db.Column(db.Integer, nullable=False, default=1)
    
    # [수정] 상수 사용
    status = db.Column(db.String(20), default=SaleStatus.VALID)
    is_online = db.Column(db.Boolean, default=False)
    
    total_amount = db.Column(db.Integer, default=0)
    payment_method = db.Column(db.String(50), default=PaymentMethod.CARD) 
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    
    items = db.relationship('SaleItem', backref='sale', lazy='dynamic', cascade="all, delete-orphan")
    store = db.relationship('Store', back_populates='sales')

    @property
    def receipt_number(self):
        return f"{self.sale_date.strftime('%Y-%m-%d')} {self.daily_number:04d}"

class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False, index=True)
    
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False)
    variant = db.relationship('Variant')
    
    product_name = db.Column(db.String(255))
    product_number = db.Column(db.String(100))
    color = db.Column(db.String(50))
    size = db.Column(db.String(50))
    
    original_price = db.Column(db.Integer, default=0)
    unit_price = db.Column(db.Integer, nullable=False)
    
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)
    
    discount_amount = db.Column(db.Integer, default=0)
    discounted_price = db.Column(db.Integer, default=0)