import io
import pandas as pd
import traceback
from datetime import datetime
from flask import request, flash, redirect, url_for, abort, send_file, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import delete

from flowork.models import db, Order, OrderProcessing, Announcement, ScheduleEvent, Staff, Setting, User, Store, Brand, Product, Variant, StoreStock, Sale, SaleItem, StockHistory
from flowork.services.db import sync_missing_data_in_db
from . import api_bp
from .utils import admin_required

@api_bp.route('/api/maintenance/export_orders', methods=['GET'])
@login_required
def export_orders_excel():
    if not current_user.store_id and not current_user.brand_id:
        abort(403)

    target_store_id = None
    if current_user.store_id:
        target_store_id = current_user.store_id
    elif current_user.brand_id:
        try:
            target_store_id = int(request.args.get('target_store_id'))
        except (TypeError, ValueError):
            target_store_id = None

    try:
        query = db.session.query(Order).join(Store).filter(Store.brand_id == current_user.current_brand_id)
        
        if target_store_id:
            query = query.filter(Order.store_id == target_store_id)

        orders = query.order_by(Order.created_at.desc()).all()

        data = []
        for o in orders:
            data.append({
                'store_name': o.store.store_name,
                'order_status': o.order_status,
                'created_at': o.created_at.strftime('%Y-%m-%d %H:%M:%S') if o.created_at else '',
                'customer_name': o.customer_name,
                'customer_phone': o.customer_phone,
                'product_number': o.product_number,
                'product_name': o.product_name,
                'color': o.color,
                'size': o.size,
                'reception_method': o.reception_method,
                'address1': o.address1,
                'address2': o.address2,
                'postcode': o.postcode,
                'courier': o.courier,
                'tracking_number': o.tracking_number,
                'completed_at': o.completed_at.strftime('%Y-%m-%d') if o.completed_at else '',
                'remarks': o.remarks
            })

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Orders')
        output.seek(0)

        filename = f"orders_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        print(f"Export Orders Error: {e}")
        traceback.print_exc()
        flash(f"주문 백업 중 오류 발생: {e}", "error")
        return redirect(url_for('ui.setting_page'))

@api_bp.route('/api/maintenance/import_orders', methods=['POST'])
@login_required
def import_orders_excel():
    if not current_user.store_id and not current_user.brand_id:
        abort(403)

    file = request.files.get('excel_file')
    if not file:
        flash('파일이 없습니다.', 'error')
        return redirect(url_for('ui.setting_page'))

    target_store_id = None
    if current_user.store_id:
        target_store_id = current_user.store_id
    elif current_user.brand_id:
        try:
            target_store_id = int(request.form.get('target_store_id'))
        except (TypeError, ValueError):
            target_store_id = None

    try:
        df = pd.read_excel(file).fillna('')
        
        success_count = 0
        for _, row in df.iterrows():
            store = None
            if target_store_id:
                store = db.session.get(Store, target_store_id)
            else:
                store_name = row.get('store_name')
                if store_name:
                    store = Store.query.filter_by(brand_id=current_user.current_brand_id, store_name=store_name).first()
            
            if not store: continue

            created_at_str = str(row.get('created_at', ''))
            try:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                created_at = datetime.now()

            completed_at_str = str(row.get('completed_at', ''))
            completed_at = None
            if completed_at_str:
                try:
                    completed_at = datetime.strptime(completed_at_str, '%Y-%m-%d')
                except ValueError:
                    pass

            product = Product.query.filter_by(brand_id=current_user.current_brand_id, product_number=row.get('product_number')).first()

            order = Order(
                store_id=store.id,
                product_id=product.id if product else None,
                order_status=row.get('order_status', '고객주문'),
                created_at=created_at,
                customer_name=row.get('customer_name'),
                customer_phone=row.get('customer_phone'),
                product_number=row.get('product_number'),
                product_name=row.get('product_name'),
                color=row.get('color'),
                size=row.get('size'),
                reception_method=row.get('reception_method', '방문수령'),
                address1=row.get('address1'),
                address2=row.get('address2'),
                postcode=str(row.get('postcode')),
                courier=row.get('courier'),
                tracking_number=row.get('tracking_number'),
                completed_at=completed_at,
                remarks=row.get('remarks')
            )
            db.session.add(order)
            success_count += 1
        
        db.session.commit()
        flash(f"{success_count}건의 주문 내역이 복구되었습니다.", "success")

    except Exception as e:
        db.session.rollback()
        print(f"Import Orders Error: {e}")
        flash(f"주문 복구 중 오류 발생: {e}", "error")

    return redirect(url_for('ui.setting_page'))

@api_bp.route('/api/reset-orders-db', methods=['POST'])
@login_required
def reset_orders_db():
    if not current_user.store_id and not current_user.brand_id:
        abort(403)

    target_store_id = None
    if current_user.store_id:
        target_store_id = current_user.store_id
    elif current_user.brand_id:
        try:
            target_store_id = int(request.form.get('target_store_id'))
        except (TypeError, ValueError):
            target_store_id = None

    try:
        if target_store_id:
            stmt = delete(OrderProcessing).where(OrderProcessing.order_id.in_(
                db.session.query(Order.id).filter(Order.store_id == target_store_id)
            ))
            db.session.execute(stmt)
            
            stmt = delete(Order).where(Order.store_id == target_store_id)
            result = db.session.execute(stmt)
            msg = f"선택한 매장의 주문 {result.rowcount}건이 삭제되었습니다."
        else:
            store_ids = db.session.query(Store.id).filter(Store.brand_id == current_user.current_brand_id).all()
            store_ids = [s[0] for s in store_ids]
            
            if store_ids:
                stmt = delete(OrderProcessing).where(OrderProcessing.order_id.in_(
                    db.session.query(Order.id).filter(Order.store_id.in_(store_ids))
                ))
                db.session.execute(stmt)

                stmt = delete(Order).where(Order.store_id.in_(store_ids))
                result = db.session.execute(stmt)
                msg = f"전체 매장의 주문 {result.rowcount}건이 삭제되었습니다."
            else:
                msg = "삭제할 주문 데이터가 없습니다."

        db.session.commit()
        flash(msg, "success")

    except Exception as e:
        db.session.rollback()
        print(f"Orders Reset Error: {e}")
        flash(f"주문 초기화 중 오류 발생: {e}", "error")
    
    return redirect(url_for('ui.setting_page'))

@api_bp.route('/api/maintenance/export_announcements', methods=['GET'])
@admin_required
def export_announcements_excel():
    if current_user.store_id: abort(403)
    
    try:
        items = Announcement.query.filter_by(brand_id=current_user.current_brand_id).order_by(Announcement.created_at.desc()).all()
        data = [{'title': i.title, 'content': i.content, 'created_at': i.created_at.strftime('%Y-%m-%d %H:%M:%S')} for i in items]
        
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        
        return send_file(output, as_attachment=True, download_name=f"notice_backup_{datetime.now().strftime('%Y%m%d')}.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        flash(f"공지사항 백업 오류: {e}", "error")
        return redirect(url_for('ui.setting_page'))

@api_bp.route('/api/maintenance/import_announcements', methods=['POST'])
@admin_required
def import_announcements_excel():
    if current_user.store_id: abort(403)
    
    file = request.files.get('excel_file')
    if not file: return redirect(url_for('ui.setting_page'))
    
    try:
        df = pd.read_excel(file).fillna('')
        count = 0
        for _, row in df.iterrows():
            created_at = datetime.now()
            try:
                if row.get('created_at'): created_at = datetime.strptime(str(row.get('created_at')), '%Y-%m-%d %H:%M:%S')
            except: pass
            
            item = Announcement(
                brand_id=current_user.current_brand_id,
                title=row.get('title'),
                content=row.get('content'),
                created_at=created_at
            )
            db.session.add(item)
            count += 1
        db.session.commit()
        flash(f"공지사항 {count}건 복구 완료", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"공지사항 복구 오류: {e}", "error")
        
    return redirect(url_for('ui.setting_page'))

@api_bp.route('/api/reset-announcements-db', methods=['POST'])
@admin_required
def reset_announcements_db():
    if current_user.store_id: abort(403)

    try:
        stmt = delete(Announcement).where(Announcement.brand_id == current_user.current_brand_id)
        db.session.execute(stmt)
        db.session.commit()
        flash("공지사항이 초기화되었습니다.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"공지사항 초기화 오류: {e}", "error")
    
    return redirect(url_for('ui.setting_page'))

@api_bp.route('/api/maintenance/export_stores', methods=['GET'])
@admin_required
def export_stores_excel():
    if current_user.store_id: abort(403)
    
    try:
        brand_id = current_user.current_brand_id
        stores = Store.query.filter_by(brand_id=brand_id).all()
        
        store_data = []
        for s in stores:
            users = User.query.filter_by(store_id=s.id).all()
            user_info = ", ".join([u.username for u in users])
            store_data.append({
                'store_code': s.store_code,
                'store_name': s.store_name,
                'phone_number': s.phone_number,
                'manager_name': s.manager_name,
                'is_active': 'Y' if s.is_active else 'N',
                'usernames': user_info
            })
            
        df = pd.DataFrame(store_data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        
        return send_file(output, as_attachment=True, download_name=f"stores_backup_{datetime.now().strftime('%Y%m%d')}.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        flash(f"매장 백업 오류: {e}", "error")
        return redirect(url_for('ui.setting_page'))

@api_bp.route('/api/maintenance/import_stores', methods=['POST'])
@admin_required
def import_stores_excel():
    if current_user.store_id: abort(403)
    
    file = request.files.get('excel_file')
    if not file: return redirect(url_for('ui.setting_page'))
    
    try:
        df = pd.read_excel(file).fillna('')
        brand_id = current_user.current_brand_id
        count = 0
        
        for _, row in df.iterrows():
            code = str(row.get('store_code', '')).strip()
            name = str(row.get('store_name', '')).strip()
            if not name: continue
            
            store = Store.query.filter_by(brand_id=brand_id, store_name=name).first()
            if not store and code:
                store = Store.query.filter_by(brand_id=brand_id, store_code=code).first()
                
            if not store:
                store = Store(
                    brand_id=brand_id,
                    store_code=code,
                    store_name=name,
                    phone_number=row.get('phone_number'),
                    manager_name=row.get('manager_name'),
                    is_active=(row.get('is_active') == 'Y'),
                    is_registered=True,
                    is_approved=True
                )
                db.session.add(store)
                db.session.flush()
                count += 1
            else:
                store.store_code = code
                store.phone_number = row.get('phone_number')
                store.manager_name = row.get('manager_name')
                store.is_active = (row.get('is_active') == 'Y')
                
        db.session.commit()
        flash(f"매장 정보 {count}건 신규 등록 (기존 매장은 업데이트)", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"매장 복구 오류: {e}", "error")
        
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
    
    return redirect(url_for('ui.stock_management'))

@api_bp.route('/sync_missing_data', methods=['POST'])
@login_required
def sync_missing_data():
    if not current_user.is_admin:
         abort(403, description="데이터 동기화는 관리자 계정만 사용할 수 있습니다.")

    success, message, category = sync_missing_data_in_db(current_user.current_brand_id)
    flash(message, category)
    
    return redirect(url_for('ui.stock_management'))

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