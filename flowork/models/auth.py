from ..extensions import db
from flask_login import UserMixin
import bcrypt
from datetime import datetime
from sqlalchemy import CheckConstraint, UniqueConstraint

class Brand(db.Model):
    __tablename__ = 'brands'
    id = db.Column(db.Integer, primary_key=True)
    brand_name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    
    stores = db.relationship('Store', back_populates='brand', lazy='dynamic', cascade="all, delete-orphan")
    users = db.relationship('User', back_populates='brand', lazy='dynamic', foreign_keys='User.brand_id', cascade="all, delete-orphan")
    settings = db.relationship('Setting', back_populates='brand', lazy='dynamic', cascade="all, delete-orphan")
    products = db.relationship('Product', backref='brand', lazy='dynamic')
    announcements = db.relationship('Announcement', backref='brand', lazy='dynamic')

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, index=True) 
    password_hash = db.Column(db.String(255), nullable=False) 
    is_admin = db.Column(db.Boolean, default=False)
    is_super_admin = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=True, index=True)
    brand = db.relationship('Brand', back_populates='users', foreign_keys=[brand_id])
    
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True, index=True)
    store = db.relationship('Store', back_populates='users', foreign_keys=[store_id])
    
    __table_args__ = (
        UniqueConstraint('username', 'brand_id', name='uq_username_brand_id'),
        CheckConstraint(
            '(is_super_admin = TRUE AND brand_id IS NULL AND store_id IS NULL) OR '
            '(is_super_admin = FALSE AND brand_id IS NOT NULL AND store_id IS NULL) OR '
            '(is_super_admin = FALSE AND brand_id IS NOT NULL AND store_id IS NOT NULL)',
            name='user_role_check'
        ),
    )
    
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    @property
    def current_brand_id(self):
        return self.brand_id