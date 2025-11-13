from ..extensions import db
from sqlalchemy import Index, UniqueConstraint
from datetime import datetime

class Product(db.Model):
    __tablename__ = 'products'
    __table_args__ = (
        Index('ix_product_brand_category', 'brand_id', 'item_category'),
        Index('ix_product_brand_year', 'brand_id', 'release_year'),
        Index('ix_product_search', 'brand_id', 'product_name_cleaned'),
        Index('ix_product_favorite', 'brand_id', 'is_favorite'),
    )
    id = db.Column(db.Integer, primary_key=True)
    product_number = db.Column(db.String(100), nullable=False, index=True) 
    product_name = db.Column(db.String(255), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=False, index=True)
    is_favorite = db.Column(db.Integer, default=0) 
    release_year = db.Column(db.Integer, nullable=True, index=True)
    item_category = db.Column(db.String, nullable=True, index=True)
    
    product_number_cleaned = db.Column(db.String, index=True)
    product_name_cleaned = db.Column(db.String, index=True)
    product_name_choseong = db.Column(db.String, index=True) 
    
    variants = db.relationship('Variant', back_populates='product', cascade="all, delete-orphan")
    orders = db.relationship('Order', backref='product_ref', lazy='dynamic')

class Variant(db.Model):
    __tablename__ = 'variants'
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(255), nullable=False, unique=True, index=True) 
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product = db.relationship('Product', back_populates='variants')
    
    color = db.Column(db.String)
    size = db.Column(db.String)
    original_price = db.Column(db.Integer, default=0)
    sale_price = db.Column(db.Integer, default=0)
    hq_quantity = db.Column(db.Integer, default=0)
    
    barcode_cleaned = db.Column(db.String, index=True, unique=True)
    color_cleaned = db.Column(db.String, index=True)
    size_cleaned = db.Column(db.String, index=True)
    
    stock_levels = db.relationship('StoreStock', back_populates='variant', cascade="all, delete-orphan")
    # [신규 2-1] 히스토리 관계 설정 (필요 시)
    stock_history = db.relationship('StockHistory', backref='variant', lazy='dynamic')
    
    __table_args__ = (Index('ix_variant_product_color_size', 'product_id', 'color', 'size'),)

class StoreStock(db.Model):
    __tablename__ = 'store_stock'
    __table_args__ = (
        Index('ix_store_stock_lookup', 'store_id', 'variant_id'),
        UniqueConstraint('store_id', 'variant_id', name='uq_store_variant'), 
    )
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False, index=True)
    
    variant = db.relationship('Variant', back_populates='stock_levels')
    quantity = db.Column(db.Integer, default=0)
    actual_stock = db.Column(db.Integer, nullable=True)

class StockHistory(db.Model):
    """
    [신규 2-1] 재고 수불부 모델
    재고가 변경될 때마다(판매, 환불, 입고, 실사조정 등) 기록을 남깁니다.
    """
    __tablename__ = 'stock_history'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # 누가 변경했는지 (시스템이면 Null일수도 있음)
    
    change_type = db.Column(db.String(50), nullable=False) # SALE, REFUND_FULL, REFUND_PARTIAL, ADJUSTMENT, CHECK_UPDATE 등
    quantity_change = db.Column(db.Integer, nullable=False) # 변동 수량 (+, -)
    current_quantity = db.Column(db.Integer, nullable=False) # 변동 후 최종 재고 (Snapshot)
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # 관계 설정 (편의상 추가)
    store = db.relationship('Store', backref=db.backref('history', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('stock_history', lazy='dynamic'))