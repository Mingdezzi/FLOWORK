from datetime import datetime, date
from ..extensions import db
from sqlalchemy import Index, UniqueConstraint

class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    work_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), nullable=False, default='출근')
    check_in_time = db.Column(db.Time, nullable=True)
    check_out_time = db.Column(db.Time, nullable=True)
    memo = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.now)
    staff = db.relationship('Staff', backref='attendances')
    __table_args__ = (UniqueConstraint('staff_id', 'work_date', name='uq_attendance_staff_date'), Index('ix_attendance_store_date', 'store_id', 'work_date'),)

class CompetitorBrand(db.Model):
    __tablename__ = 'competitor_brands'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)

class CompetitorSale(db.Model):
    __tablename__ = 'competitor_sales'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    competitor_id = db.Column(db.Integer, db.ForeignKey('competitor_brands.id'), nullable=False)
    sale_date = db.Column(db.Date, nullable=False, default=date.today)
    offline_normal = db.Column(db.Integer, default=0)
    offline_event = db.Column(db.Integer, default=0)
    online_normal = db.Column(db.Integer, default=0)
    online_event = db.Column(db.Integer, default=0)
    competitor = db.relationship('CompetitorBrand', backref='sales')
    __table_args__ = (UniqueConstraint('store_id', 'competitor_id', 'sale_date', name='uq_comp_sale_key'), Index('ix_comp_sale_store_date', 'store_id', 'sale_date'),)