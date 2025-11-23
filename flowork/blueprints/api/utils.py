from functools import wraps
from flask import abort
from flask_login import current_user, login_required
from flowork.models import db, StoreStock
from sqlalchemy import exc
from datetime import datetime

def admin_required(f):
    @wraps(f)
    @login_required 
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin and not current_user.is_super_admin:
            abort(403, description="이 작업을 수행할 관리자 권한이 없습니다.")
        return f(*args, **kwargs)
    return decorated_function

def _get_or_create_store_stock(variant_id, store_id):
    stock = db.session.query(StoreStock).filter_by(
        variant_id=variant_id,
        store_id=store_id
    ).first()
    
    if stock:
        return stock

    try:
        stock = StoreStock(
            variant_id=variant_id,
            store_id=store_id,
            quantity=0,
            actual_stock=None
        )
        db.session.add(stock)
        db.session.commit() 
        return stock
    except exc.IntegrityError:
        db.session.rollback()
        stock = db.session.query(StoreStock).filter_by(
            variant_id=variant_id,
            store_id=store_id
        ).first()
        return stock

def _parse_iso_date_string(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.split('T')[0], '%Y-%m-%d').date()
    except ValueError:
        print(f"Warning: Could not parse date string {date_str}")
        return None