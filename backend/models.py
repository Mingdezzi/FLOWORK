# backend/models.py
from datetime import datetime
from . import db

class Brand(db.Model):
    __tablename__ = 'brands'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    stores = db.relationship('Store', backref='brand', lazy='dynamic')
    products = db.relationship('Product', backref='brand', lazy='dynamic')

class Store(db.Model):
    __tablename__ = 'stores'
    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_hq = db.Column(db.Boolean, default=False) # 본사(창고) 여부
    is_active = db.Column(db.Boolean, default=True)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True)
    role = db.Column(db.String(20), default='staff') # 'super_admin', 'brand_admin', 'store_manager', 'staff'

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=False)
    
    product_code = db.Column(db.String(50), nullable=False, index=True) # 품번 (기존 product_number)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    release_year = db.Column(db.Integer, nullable=True)
    
    # 검색 최적화를 위한 필드
    search_code = db.Column(db.String(50), index=True) # 공백/특수문자 제거된 품번
    
    variants = db.relationship('Variant', backref='product', cascade='all, delete-orphan')

class Variant(db.Model):
    __tablename__ = 'variants'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    barcode = db.Column(db.String(50), unique=True, nullable=False, index=True)
    color = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(50), nullable=False)
    
    cost_price = db.Column(db.Integer, default=0) # 원가/최초가
    sale_price = db.Column(db.Integer, default=0) # 판매가

class Stock(db.Model):
    """통합 재고 테이블 (본사/매장 모두 사용)"""
    __tablename__ = 'stocks'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False)
    
    quantity = db.Column(db.Integer, default=0) # 전산 재고
    
    __table_args__ = (db.UniqueConstraint('store_id', 'variant_id'),)

class PosOrder(db.Model):
    """매장 판매 기록 (기존 Sale)"""
    __tablename__ = 'pos_orders'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    order_number = db.Column(db.String(50), unique=True, nullable=False) # 영수증 번호
    total_amount = db.Column(db.Integer, default=0)
    payment_method = db.Column(db.String(20), default='CARD')
    status = db.Column(db.String(20), default='COMPLETED') # COMPLETED, REFUNDED
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    items = db.relationship('PosOrderItem', backref='order', cascade='all, delete-orphan')

class PosOrderItem(db.Model):
    __tablename__ = 'pos_order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('pos_orders.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False)
    
    product_name_snapshot = db.Column(db.String(200)) # 판매 시점 상품명 보존
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Integer, nullable=False) # 판매 시점 단가
    subtotal = db.Column(db.Integer, nullable=False)