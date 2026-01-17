from flask_sqlalchemy import SQLAlchemy
# (수정) CheckConstraint, UniqueConstraint 임포트
from sqlalchemy import Integer, String, DateTime, func, Text, ForeignKey, Boolean, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime 
import bcrypt 
from flask_login import UserMixin 

db = SQLAlchemy()

# --- 1. 계정/소유자 모델 ---

class Brand(db.Model):
    """
    최상위 계정 (테넌트). 예: 'FLOWORK', 'Nike'
    """
    __tablename__ = 'brands'
    id = db.Column(Integer, primary_key=True)
    brand_name = db.Column(String(100), nullable=False, unique=True)
    created_at = db.Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # [수정] 이 브랜드가 소유한 매장 (back_populates 명시)
    stores = db.relationship('Store', back_populates='brand', lazy='dynamic', cascade="all, delete-orphan")
    
    # [신규] 이 브랜드에 소속된 (본사 및 매장) 유저들
    users = db.relationship('User', back_populates='brand', lazy='dynamic', 
                              foreign_keys='User.brand_id',
                              cascade="all, delete-orphan")

    products = db.relationship('Product', backref='brand', lazy='dynamic')
    announcements = db.relationship('Announcement', backref='brand', lazy='dynamic')

class Store(db.Model):
    """
    실제 사용자가 속한 매장 (서브 테넌트). 예: '강남점', '명동점'
    """
    __tablename__ = 'stores'
    id = db.Column(Integer, primary_key=True)
    store_name = db.Column(String(100), nullable=False)
    phone_number = db.Column(String(50), nullable=True)
    
    # [삭제] is_hq = db.Column(Boolean, default=False) <-- 삭제

    # 이 매장이 속한 브랜드 (소유주)
    brand_id = db.Column(Integer, db.ForeignKey('brands.id'), nullable=False, index=True)
    # [수정] brand와의 관계를 back_populates로 명시
    brand = db.relationship('Brand', back_populates='stores')

    # [수정] 이 매장에 속한 사용자 계정들 (back_populates 명시)
    users = db.relationship('User', back_populates='store', lazy='dynamic', foreign_keys='User.store_id')
    
    # 이 매장이 소유한 것들
    orders = db.relationship('Order', backref='store', lazy='dynamic')
    stock_levels = db.relationship('StoreStock', backref='store', lazy='dynamic', foreign_keys='StoreStock.store_id')
    settings = db.relationship('Setting', backref='store', lazy='dynamic')
    
    staff_members = db.relationship('Staff', backref='store', lazy='dynamic', cascade="all, delete-orphan")
    schedule_events = db.relationship('ScheduleEvent', backref='store', lazy='dynamic', cascade="all, delete-orphan") 
    
    received_processings = db.relationship('OrderProcessing', backref='source_store', lazy='dynamic', foreign_keys='OrderProcessing.source_store_id')

# (수정) UserMixin 추가 (flask-login을 위해)
class User(db.Model, UserMixin):
    """
    실제 로그인하는 사용자 계정
    """
    __tablename__ = 'users'
    id = db.Column(Integer, primary_key=True)
    
    # [수정] unique=True 제거. (브랜드별 유일성은 하단 UniqueConstraint에서 처리)
    username = db.Column(String(80), nullable=False, index=True) # 로그인 ID
    password_hash = db.Column(String(255), nullable=False) # 해시된 비밀번호
    
    # [수정] '매장' 또는 '본사'의 관리자 여부
    is_admin = db.Column(Boolean, default=False)
    
    # [신규] 슈퍼 관리자 여부
    is_super_admin = db.Column(Boolean, default=False, nullable=False, index=True)

    # [신규/수정]
    # '본사 계정'과 '매장 계정' 모두 소속 Brand ID를 가짐.
    # '슈퍼 관리자'만 이 값이 NULL.
    brand_id = db.Column(Integer, db.ForeignKey('brands.id'), nullable=True, index=True)
    brand = db.relationship('Brand', back_populates='users', foreign_keys=[brand_id])

    # [수정]
    # '매장 계정'만 소속 Store ID를 가짐.
    # '본사 계정', '슈퍼 관리자'는 이 값이 NULL. (nullable=True로 변경)
    store_id = db.Column(Integer, db.ForeignKey('stores.id'), nullable=True, index=True)
    store = db.relationship('Store', back_populates='users', foreign_keys=[store_id])


    __table_args__ = (
        # [신규] (요구사항 5)
        # 1. 슈퍼 관리자가 아닐 경우 (brand_id가 NULL이 아님)
        # 2. username과 brand_id의 조합은 유일해야 함.
        UniqueConstraint('username', 'brand_id', name='uq_username_brand_id'),
        
        # [신규] 3가지 계정 유형을 DB에서 강제
        CheckConstraint(
            # 1. 슈퍼 관리자 (super_admin=True, brand/store=NULL)
            '(is_super_admin = TRUE AND brand_id IS NULL AND store_id IS NULL) OR '
            # 2. 본사 계정 (super_admin=False, brand_id=NOT NULL, store_id=NULL)
            '(is_super_admin = FALSE AND brand_id IS NOT NULL AND store_id IS NULL) OR '
            # 3. 매장 계정 (super_admin=False, brand_id=NOT NULL, store_id=NOT NULL)
            '(is_super_admin = FALSE AND brand_id IS NOT NULL AND store_id IS NOT NULL)',
            name='user_role_check'
        ),
    )


    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    # [신규] 헬퍼 프로퍼티: 현재 유저의 유효한 brand_id를 반환 (라우트에서 사용)
    @property
    def current_brand_id(self):
        """현재 유저가 속한 Brand의 ID를 반환 (슈퍼 관리자는 None)"""
        # brand_id는 본사/매장 계정 모두 가지고 있으므로 그대로 반환
        return self.brand_id


# --- 2. 브랜드 종속 데이터 (카탈로그) ---

class Product(db.Model):
    """
    상품 카탈로그 (브랜드가 소유)
    (수정) 기본 키를 품번 대신 id(Integer)로 변경
    """
    __tablename__ = 'products'
    # (수정) 권장 복합 인덱스 추가
    __table_args__ = (
        Index('ix_product_brand_category', 'brand_id', 'item_category'),
        Index('ix_product_brand_year', 'brand_id', 'release_year'),
    )
    
    id = db.Column(Integer, primary_key=True)
    product_number = db.Column(String(100), nullable=False, index=True) # 품번
    product_name = db.Column(String(255), nullable=False)
    
    # 이 상품을 소유한 브랜드 (소유주)
    brand_id = db.Column(Integer, db.ForeignKey('brands.id'), nullable=False, index=True)
    
    is_favorite = db.Column(Integer, default=0) # (참고: 매장별 즐겨찾기로 변경 필요)
    release_year = db.Column(Integer, nullable=True, index=True)
    item_category = db.Column(String, nullable=True, index=True)
    
    product_number_cleaned = db.Column(String, index=True)
    product_name_cleaned = db.Column(String, index=True)
    product_name_choseong = db.Column(String, index=True) 
    
    # (수정) lazy='dynamic' 제거 (N+1 오류 해결 위함)
    variants = db.relationship('Variant', backref='product', cascade="all, delete-orphan")
    orders = db.relationship('Order', backref='product_ref', lazy='dynamic')

class Variant(db.Model):
    """
    상품 옵션 (SKU). 예: Air Max 90 / 001 / 270
    (수정) 기본 키를 바코드 대신 id(Integer)로 변경
    """
    __tablename__ = 'variants'
    id = db.Column(Integer, primary_key=True)
    barcode = db.Column(String(255), nullable=False, unique=True, index=True) # 바코드 (SKU)
    
    # 이 옵션이 속한 상품 (소유주)
    product_id = db.Column(Integer, db.ForeignKey('products.id'), nullable=False)
    
    color = db.Column(String)
    size = db.Column(String)
    original_price = db.Column(Integer, default=0)
    sale_price = db.Column(Integer, default=0)
    
    # (삭제) store_stock, hq_stock, actual_stock -> 'StoreStock' 테이블로 이동됨
    
    barcode_cleaned = db.Column(String, index=True, unique=True)
    color_cleaned = db.Column(String, index=True)
    size_cleaned = db.Column(String, index=True)

    # (수정) lazy='dynamic' 제거 (N+1 오류 해결 위함)
    stock_levels = db.relationship('StoreStock', backref='variant')

# --- 3. 매장 종속 데이터 (운영) ---

class StoreStock(db.Model):
    """
    (신규) 매장별 재고 테이블
    """
    __tablename__ = 'store_stock'
    # (수정) 복합 인덱스 추가
    __table_args__ = (
        Index('ix_store_stock_lookup', 'store_id', 'variant_id'),
    )
    
    id = db.Column(Integer, primary_key=True)
    
    # 어느 매장의 재고인가? (소유주)
    store_id = db.Column(Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    
    # 무슨 상품의 재고인가?
    variant_id = db.Column(Integer, db.ForeignKey('variants.id'), nullable=False, index=True)
    
    # 재고 수량
    quantity = db.Column(Integer, default=0)
    actual_stock = db.Column(Integer, nullable=True) # 실사재고

class Staff(db.Model):
    """
    (신규) 매장 직원
    """
    __tablename__ = 'staff'
    id = db.Column(Integer, primary_key=True)
    
    # 이 직원이 속한 매장 (소유주)
    store_id = db.Column(Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    
    name = db.Column(String(100), nullable=False) # 직원이름
    position = db.Column(String(100), nullable=True) # 직원직책
    contact = db.Column(String(50), nullable=True) # 연락처
    is_active = db.Column(Boolean, default=True) # 재직 여부 (삭제 대신)
    
    created_at = db.Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # 이 직원의 일정
    schedules = db.relationship('ScheduleEvent', backref='staff', lazy='dynamic', foreign_keys='ScheduleEvent.staff_id')

class ScheduleEvent(db.Model):
    """
    (수정) 매장별 일정 (캘린더)
    """
    __tablename__ = 'schedule_events'
    __table_args__ = (
        # (신규) 일정 조회를 위한 복합 인덱스
        Index('ix_schedule_store_staff_time', 'store_id', 'staff_id', 'start_time'), 
    )
    id = db.Column(Integer, primary_key=True)
    
    # 이 일정이 속한 매장 (소유주)
    store_id = db.Column(Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    
    # (신규) 이 일정이 속한 직원 (매장 전체 일정의 경우 Null)
    staff_id = db.Column(Integer, db.ForeignKey('staff.id', ondelete='SET NULL'), nullable=True, index=True)
    
    title = db.Column(String(255), nullable=False) # 일정 제목
    
    # (신규) 일정 분류 (일정, 휴무, 반차, 연차, 병가)
    event_type = db.Column(String(50), nullable=False, default='일정', index=True)
    
    start_time = db.Column(DateTime(timezone=True), nullable=False, index=True) # 시작 시간
    end_time = db.Column(DateTime(timezone=True), nullable=True) # 종료 시간 (하루 종일이 아닐 경우)
    all_day = db.Column(Boolean, default=True) # 하루 종일 여부 (기본값 True)
    color = db.Column(String(20), nullable=True) # 이벤트 색상 (FullCalendar 용)
    
    created_at = db.Column(DateTime(timezone=True), default=datetime.utcnow)

class Order(db.Model):
    """
    주문 내역 (매장이 소유)
    """
    __tablename__ = 'orders'
    # (수정) 복합 인덱스 추가 (기존 것과 권장 사항 통합)
    __table_args__ = (
        Index('ix_order_store_status', 'store_id', 'order_status'),
        Index('ix_order_created', 'created_at'),
        Index('ix_order_store_created', 'store_id', 'created_at'), # (신규) 권장 인덱스
    )
    
    id = db.Column(Integer, primary_key=True)
    
    # 이 주문을 등록한 매장 (소유주)
    store_id = db.Column(Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    
    # 주문 상품 (참고: 상품이 삭제돼도 주문은 남아야 하므로, key는 Nullable, 정보는 복사)
    # (수정) ondelete='SET NULL' 추가
    product_id = db.Column(Integer, db.ForeignKey('products.id', ondelete='SET NULL'), nullable=True) # 상품 삭제 대비
    product_number = db.Column(String, nullable=False) # 품번 복사
    product_name = db.Column(String, nullable=False) # 품명 복사
    color = db.Column(String) # 컬러 복사
    size = db.Column(String) # 사이즈 복사
    
    # 고객 정보
    customer_name = db.Column(String, nullable=False)
    customer_phone = db.Column(String, nullable=False)

    # (기존 필드 유지)
    created_at = db.Column(DateTime(timezone=True), default=datetime.utcnow) 
    completed_at = db.Column(DateTime(timezone=True), nullable=True) 
    reception_method = db.Column(String(50), nullable=False, default='방문수령') 
    postcode = db.Column(String(10))
    address1 = db.Column(String(255))
    address2 = db.Column(String(255)) 
    order_status = db.Column(String(50), default='고객주문') 
    remarks = db.Column(Text, nullable=True) 
    courier = db.Column(String(100), nullable=True)
    tracking_number = db.Column(String(100), nullable=True)
    
    # (삭제) order_source (Store ID로 대체됨)

    processing_steps = db.relationship('OrderProcessing', backref='order', lazy='dynamic', cascade="all, delete-orphan")

class OrderProcessing(db.Model):
    """
    주문 처리 내역 (타 매장 발주)
    """
    __tablename__ = 'order_processing'
    id = db.Column(Integer, primary_key=True)
    
    # 이 처리가 속한 주문 (소유주)
    order_id = db.Column(Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    
    # 발주를 넣은 '타 매장' (Store 테이블 참조)
    # (수정) ondelete='CASCADE' 추가
    source_store_id = db.Column(Integer, db.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False, index=True)
    
    source_result = db.Column(String(50), nullable=True) # 예: '완료', '불가'

class Setting(db.Model):
    """
    매장별 설정값 (매장이 소유)
    (수정) Setting 테이블 구조 변경
    """
    __tablename__ = 'settings'
    id = db.Column(Integer, primary_key=True)
    
    # 이 설정이 속한 매장 (소유주)
    store_id = db.Column(Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    
    key = db.Column(String(100), nullable=False, index=True) # 예: 'SMS_BRAND_NAME'
    value = db.Column(Text, nullable=True)

class Announcement(db.Model):
    """
    공지사항 (브랜드가 소유)
    """
    __tablename__ = 'announcements'
    id = db.Column(Integer, primary_key=True)
    
    # 이 공지를 올린 브랜드 (소유주)
    brand_id = db.Column(Integer, db.ForeignKey('brands.id'), nullable=False, index=True)
    
    title = db.Column(String(255), nullable=False)
    content = db.Column(Text, nullable=False)
    created_at = db.Column(DateTime(timezone=True), default=datetime.utcnow)