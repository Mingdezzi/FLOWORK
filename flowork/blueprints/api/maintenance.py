import traceback
from flask import request, flash, redirect, url_for, abort
from flask_login import login_required, current_user

from flowork.models import db, Order, OrderProcessing, Announcement, ScheduleEvent, Staff, Setting, User, Store, Brand, Product, Variant, StoreStock, Sale, SaleItem, StockHistory
from flowork.services.db import sync_missing_data_in_db
from . import api_bp
from .utils import admin_required

@api_bp.route('/api/reset-orders-db', methods=['POST'])
@admin_required
def reset_orders_db():
    if not current_user.store_id:
        abort(403, description="주문 DB 초기화는 매장 관리자만 가능합니다.")

    try:
        engine = db.get_engine(bind=None)
        if engine is None:
            raise Exception("Default bind engine not found.")

        tables_to_drop = [
            OrderProcessing.__table__, 
            Order.__table__,
        ]
        
        db.Model.metadata.drop_all(bind=engine, tables=tables_to_drop, checkfirst=True)
        db.Model.metadata.create_all(bind=engine, tables=tables_to_drop, checkfirst=True)
        
        flash("✅ '주문(Orders)' 테이블이 성공적으로 초기화되었습니다.", "success")

    except Exception as e:
        db.session.rollback()
        print(f"Orders DB Reset Error: {e}")
        traceback.print_exc()
        flash(f"🚨 주문 DB 초기화 중 오류 발생: {e}", "error")
    
    return redirect(url_for('ui.setting_page'))

@api_bp.route('/api/reset-announcements-db', methods=['POST'])
@admin_required
def reset_announcements_db():
    if not current_user.brand_id or current_user.store_id:
        abort(403, description="공지사항 DB 초기화는 본사 관리자만 가능합니다.")

    try:
        engine = db.get_engine(bind=None)
        if engine is None:
            raise Exception("Default bind engine not found.")

        tables_to_drop = [Announcement.__table__]
        
        db.Model.metadata.drop_all(bind=engine, tables=tables_to_drop, checkfirst=True)
        db.Model.metadata.create_all(bind=engine, tables=tables_to_drop, checkfirst=True)
        
        flash("✅ '공지사항(Announcements)' 테이블이 성공적으로 초기화되었습니다.", "success")

    except Exception as e:
        db.session.rollback()
        print(f"Announcements DB Reset Error: {e}")
        traceback.print_exc()
        flash(f"🚨 공지사항 DB 초기화 중 오류 발생: {e}", "error")
    
    return redirect(url_for('ui.setting_page'))

@api_bp.route('/api/reset-store-db', methods=['POST'])
@admin_required
def reset_store_db():
    if not current_user.is_super_admin:
        abort(403, description="전체 시스템 초기화는 슈퍼 관리자만 가능합니다.")

    try:
        engine = db.get_engine(bind=None)
        if engine is None:
            raise Exception("Default bind engine not found.")

        tables_to_drop = [
            ScheduleEvent.__table__, 
            Staff.__table__,
            Setting.__table__, 
            User.__table__, 
            Store.__table__, 
            Brand.__table__
        ]
        
        db.Model.metadata.drop_all(bind=engine, tables=tables_to_drop, checkfirst=True)
        db.Model.metadata.create_all(bind=engine, tables=tables_to_drop, checkfirst=True)
        
        flash("✅ '계정/매장/설정/직원/일정' 테이블이 성공적으로 초기화되었습니다. (모든 계정 삭제됨)", "success")

    except Exception as e:
        db.session.rollback()
        print(f"Store Info DB Reset Error: {e}")
        traceback.print_exc()
        flash(f"🚨 계정/매장 DB 초기화 중 오류 발생: {e}", "error")
    
    return redirect(url_for('ui.setting_page'))

@api_bp.route('/reset_database_completely', methods=['POST'])
@admin_required
def reset_database_completely():
    if not current_user.brand_id or current_user.store_id:
        abort(403, description="상품 데이터 초기화는 본사 관리자만 가능합니다.")
        
    try:
        db.session.query(Order).update({Order.product_id: None})
        
        db.session.query(StockHistory).delete()
        db.session.query(SaleItem).delete()
        db.session.query(Sale).delete()
        db.session.query(StoreStock).delete()
        db.session.query(Variant).delete()
        db.session.query(Product).delete()
        
        db.session.commit()
        
        db.create_all()
        
        flash('상품 데이터 초기화 완료. (상품/옵션/재고/매출/재고이력 삭제됨. 계정/주문 내역 보존)', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'DB 초기화 오류: {e}', 'error')
        print(f"DB Reset Error: {e}")
        traceback.print_exc()
    return redirect(url_for('ui.setting_page'))

@api_bp.route('/sync_missing_data', methods=['POST'])
@login_required
def sync_missing_data():
    if not current_user.is_admin:
         abort(403, description="데이터 동기화는 관리자 계정만 사용할 수 있습니다.")

    success, message, category = sync_missing_data_in_db(current_user.current_brand_id)
    flash(message, category)
    
    if current_user.store_id:
        return redirect(url_for('ui.stock_management'))
    else:
        return redirect(url_for('ui.setting_page'))

@api_bp.route('/reset_actual_stock', methods=['POST'])
@login_required
def reset_actual_stock():
    target_store_id = None
    
    if current_user.store_id:
        target_store_id = current_user.store_id
    elif current_user.is_admin:
        target_store_id = request.form.get('target_store_id', type=int)
        
    if not target_store_id:
        abort(403, description="초기화할 매장 정보를 확인할 수 없습니다.")

    try: 
        store_stock_ids_query = db.session.query(StoreStock.id).filter_by(store_id=target_store_id)
        
        stmt = db.update(StoreStock).where(
            StoreStock.id.in_(store_stock_ids_query)
        ).values(actual_stock=None)
        
        result = db.session.execute(stmt)
        db.session.commit()
        flash(f'실사재고 {result.rowcount}건 초기화 완료.', 'success')
    except Exception as e: 
        db.session.rollback()
        flash(f'초기화 오류: {e}', 'error')
        
    return redirect(url_for('ui.check_page', target_store_id=target_store_id if not current_user.store_id else None))