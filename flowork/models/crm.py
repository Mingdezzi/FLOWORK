from datetime import datetime
from ..extensions import db
from sqlalchemy import Index

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True) # 연락처로 검색
    address = db.Column(db.String(255), nullable=True)
    
    # 고객번호 (자동생성 예: C-YYYYMMDD-001)
    customer_code = db.Column(db.String(50), unique=True, nullable=False)
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    
    # 관계 설정
    repairs = db.relationship('Repair', backref='customer', lazy='dynamic', cascade="all, delete-orphan")
    # 추후 Sale 모델과 연동하여 구매 이력을 가져올 수 있음 (현재는 단순 DB화)

class Repair(db.Model):
    __tablename__ = 'repairs'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    
    reception_date = db.Column(db.Date, nullable=False, default=datetime.now)
    
    # 상품 정보 (DB에 없는 상품일 수도 있으므로 텍스트로 저장하거나 선택)
    product_info = db.Column(db.String(255), nullable=True) 
    product_code = db.Column(db.String(100), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    size = db.Column(db.String(50), nullable=True)
    
    description = db.Column(db.Text, nullable=True) # 수선 내용
    
    # 처리 과정: 접수 -> 본사입고 -> 수선처리 -> 처리완료 -> 매장입고 -> 고객회수 (또는 회수거부, 재접수, 기타)
    status = db.Column(db.String(20), default='접수', nullable=False)
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.now)
    
    # 관계 설정
    store = db.relationship('Store', backref='repairs')

    __table_args__ = (
        Index('ix_repair_store_status', 'store_id', 'status'),
    )