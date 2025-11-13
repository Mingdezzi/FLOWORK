import json
import os
import traceback
from flask import request, jsonify, current_app, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import func, exc

# [수정] Sale, SaleItem 모델 추가 임포트
from flowork.models import db, Brand, Store, Setting, User, Staff, Order, OrderProcessing, Announcement, ScheduleEvent, Variant, Product, StoreStock, Sale, SaleItem
from . import api_bp
from .utils import admin_required

@api_bp.route('/api/setting/brand_name', methods=['POST'])
@admin_required
def update_brand_name():
    if not current_user.brand_id or current_user.store_id:
        abort(403, description="브랜드 이름 설정은 본사 관리자만 가능합니다.")

    data = request.json
    brand_name = data.get('brand_name', '').strip()
    
    if not brand_name:
        return jsonify({'status': 'error', 'message': '브랜드 이름이 비어있습니다.'}), 400
        
    try:
        current_brand_id = current_user.current_brand_id
        
        brand = db.session.get(Brand, current_brand_id)
        if not brand:
            return jsonify({'status': 'error', 'message': '브랜드를 찾을 수 없습니다.'}), 404
            
        brand.brand_name = brand_name
        
        brand_name_setting = Setting.query.filter_by(
            brand_id=current_brand_id, 
            key='BRAND_NAME'
        ).first()
        if not brand_name_setting:
            brand_name_setting = Setting(brand_id=current_brand_id, key='BRAND_NAME')
            db.session.add(brand_name_setting)
        brand_name_setting.value = brand_name
        
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'message': f"브랜드 이름이 '{brand_name}'(으)로 저장되었습니다.",
            'brand_name': brand_name
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating brand name: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500

@api_bp.route('/api/setting/load_from_file', methods=['POST'])
@admin_required
def load_settings_from_file():
    if not current_user.brand_id:
        return jsonify({'status': 'error', 'message': '브랜드 관리자만 사용할 수 있습니다.'}), 403
    
    if current_user.store_id:
        return jsonify({'status': 'error', 'message': '본사 관리자만 설정을 변경할 수 있습니다.'}), 403

    try:
        brand = db.session.get(Brand, current_user.brand_id)
        filename = f"{brand.brand_name}.json"
        
        base_dir = current_app.root_path 
        file_path = os.path.join(base_dir, 'brands', filename)
        
        if not os.path.exists(file_path):
             return jsonify({'status': 'error', 'message': f"설정 파일 '{filename}'을(를) 'flowork/brands/' 폴더에서 찾을 수 없습니다."}), 404
             
        with open(file_path, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
            
        updated_count = 0
        for key, value in settings_data.items():
            if isinstance(value, (dict, list)):
                str_value = json.dumps(value, ensure_ascii=False)
            else:
                str_value = str(value)
                
            setting = Setting.query.filter_by(brand_id=brand.id, key=key).first()
            if setting:
                setting.value = str_value
            else:
                new_setting = Setting(brand_id=brand.id, key=key, value=str_value)
                db.session.add(new_setting)
            updated_count += 1
                
        db.session.commit()
        return jsonify({'status': 'success', 'message': f"'{filename}' 파일에서 {updated_count}개의 설정을 로드하여 적용했습니다."})
        
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'message': '설정 파일이 올바른 JSON 형식이 아닙니다.'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error loading settings from file: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'설정 로드 중 오류: {e}'}), 500

@api_bp.route('/api/setting', methods=['POST'])
@admin_required
def update_setting():
    if not current_user.brand_id:
        return jsonify({'status': 'error', 'message': '브랜드 관리자만 사용할 수 있습니다.'}), 403
    if current_user.store_id:
        return jsonify({'status': 'error', 'message': '본사 관리자만 설정을 변경할 수 있습니다.'}), 403

    data = request.json
    key = data.get('key')
    value = data.get('value') 

    if not key:
        return jsonify({'status': 'error', 'message': '설정 키(key)가 필요합니다.'}), 400

    try:
        if isinstance(value, (dict, list)):
            str_value = json.dumps(value, ensure_ascii=False)
        else:
            str_value = str(value)

        setting = Setting.query.filter_by(
            brand_id=current_user.brand_id, 
            key=key
        ).first()

        if setting:
            setting.value = str_value
        else:
            new_setting = Setting(brand_id=current_user.brand_id, key=key, value=str_value)
            db.session.add(new_setting)
        
        db.session.commit()
        return jsonify({'status': 'success', 'message': '설정이 저장되었습니다.'})

    except Exception as e:
        db.session.rollback()
        print(f"Setting update error: {e}")
        return jsonify({'status': 'error', 'message': f'설정 저장 중 오류: {e}'}), 500


@api_bp.route('/api/stores', methods=['GET'])
@login_required
def get_stores():
    if current_user.is_super_admin:
         return jsonify({'status': 'error', 'message': '슈퍼 관리자는 이 API를 사용할 수 없습니다.'}), 403

    try:
        stores = Store.query.filter_by(
            brand_id=current_user.current_brand_id 
        ).order_by(Store.store_name).all()
        
        return jsonify({
            'status': 'success',
            'stores': [{
                'id': s.id, 
                'store_code': s.store_code or '',
                'store_name': s.store_name,
                'phone_number': s.phone_number or '',
                'manager_name': s.manager_name or '',
                'is_registered': s.is_registered,
                'is_approved': s.is_approved,
                'is_active': s.is_active
            } for s in stores]
        })
    except Exception as e:
        print(f"Error getting stores: {e}")
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500

@api_bp.route('/api/stores', methods=['POST'])
@admin_required
def add_store():
    if not current_user.brand_id or current_user.store_id:
        abort(403, description="매장 추가는 본사 관리자만 가능합니다.")

    data = request.json
    code = data.get('store_code', '').strip()
    name = data.get('store_name', '').strip()
    phone = data.get('store_phone', '').strip()

    if not name or not code:
        return jsonify({'status': 'error', 'message': '매장 코드와 이름은 필수입니다.'}), 400
    
    try:
        current_brand_id = current_user.current_brand_id
        
        existing_code = Store.query.filter(
            Store.brand_id == current_brand_id, 
            Store.store_code == code
        ).first()
        if existing_code:
            return jsonify({'status': 'error', 'message': f"매장 코드 '{code}'(이)가 이미 존재합니다."}), 409
            
        existing_name = Store.query.filter(
            Store.brand_id == current_brand_id, 
            func.lower(Store.store_name) == func.lower(name)
        ).first()
        if existing_name:
            return jsonify({'status': 'error', 'message': f"매장 이름 '{name}'(이)가 이미 존재합니다."}), 409

        new_store = Store(
            brand_id=current_brand_id, 
            store_code=code,
            store_name=name,
            phone_number=phone,
            is_registered=False,
            is_approved=False,
            is_active=True
        )
        db.session.add(new_store)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f"'{name}'(이)가 추가되었습니다. (가입 대기 상태)",
            'store': {
                'id': new_store.id, 
                'store_code': new_store.store_code or '',
                'store_name': new_store.store_name,
                'phone_number': new_store.phone_number or '',
                'manager_name': new_store.manager_name or '',
                'is_registered': new_store.is_registered,
                'is_approved': new_store.is_approved,
                'is_active': new_store.is_active
            }
        }), 201 
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding store: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500

@api_bp.route('/api/stores/<int:store_id>', methods=['POST'])
@admin_required
def update_store(store_id):
    if not current_user.brand_id or current_user.store_id:
        abort(403, description="매장 수정은 본사 관리자만 가능합니다.")

    data = request.json
    code = data.get('store_code', '').strip()
    name = data.get('store_name', '').strip()
    phone = data.get('store_phone', '').strip()

    if not name or not code:
         return jsonify({'status': 'error', 'message': '매장 코드와 이름은 필수입니다.'}), 400

    try:
        current_brand_id = current_user.current_brand_id

        store = Store.query.filter_by(
            id=store_id, 
            brand_id=current_brand_id
        ).first()
        
        if not store:
            return jsonify({'status': 'error', 'message': '수정할 매장을 찾을 수 없습니다.'}), 404

        existing_code = Store.query.filter(
            Store.brand_id == current_brand_id, 
            Store.store_code == code,
            Store.id != store_id
        ).first()
        if existing_code:
            return jsonify({'status': 'error', 'message': f"매장 코드 '{code}'(이)가 이미 존재합니다."}), 409

        existing_name = Store.query.filter(
            Store.brand_id == current_brand_id, 
            func.lower(Store.store_name) == func.lower(name),
            Store.id != store_id
        ).first()
        if existing_name:
            return jsonify({'status': 'error', 'message': f"매장 이름 '{name}'(이)가 이미 존재합니다."}), 409

        store.store_code = code
        store.store_name = name
        store.phone_number = phone
        db.session.commit()
        message = f"'{name}' 정보가 수정되었습니다."

        return jsonify({
            'status': 'success',
            'message': message,
            'store': {
                'id': store.id, 
                'store_code': store.store_code or '',
                'store_name': store.store_name,
                'phone_number': store.phone_number or '',
                'manager_name': store.manager_name or '',
                'is_registered': store.is_registered,
                'is_approved': store.is_approved,
                'is_active': store.is_active
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating store: {e}")
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500


@api_bp.route('/api/stores/<int:store_id>', methods=['DELETE'])
@admin_required
def delete_store(store_id):
    if not current_user.brand_id or current_user.store_id:
        abort(403, description="매장 삭제는 본사 관리자만 가능합니다.")

    try:
        store = Store.query.filter_by(
            id=store_id, 
            brand_id=current_user.current_brand_id
        ).first()
        
        if not store:
            return jsonify({'status': 'error', 'message': '삭제할 매장을 찾을 수 없습니다.'}), 404
        
        if store.is_registered:
            return jsonify({'status': 'error', 'message': f"'{store.store_name}'(은)는 매장 사용자가 등록 신청한 내역이 있어 삭제할 수 없습니다. '등록 초기화'를 먼저 실행하세요."}), 403

        name = store.store_name
        db.session.delete(store)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f"'{name}'(이)가 삭제되었습니다."
        })
        
    except exc.IntegrityError:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f"'{name}'(은)는 현재 주문/재고 내역에서 사용 중이므로 삭제할 수 없습니다."}), 409
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting store: {e}")
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500

@api_bp.route('/api/stores/approve/<int:store_id>', methods=['POST'])
@admin_required
def approve_store(store_id):
    if not current_user.brand_id or current_user.store_id:
        abort(403, description="매장 승인은 본사 관리자만 가능합니다.")

    try:
        store = Store.query.filter_by(
            id=store_id, 
            brand_id=current_user.current_brand_id
        ).first()
        
        if not store:
            return jsonify({'status': 'error', 'message': '매장을 찾을 수 없습니다.'}), 404
        
        if not store.is_registered:
             return jsonify({'status': 'error', 'message': '아직 매장 담당자가 가입 신청을 하지 않았습니다.'}), 400
        
        store.is_approved = True
        store.is_active = True 
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': f"'{store.store_name}' 매장의 가입을 승인했습니다."})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error approving store: {e}")
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500

@api_bp.route('/api/stores/toggle_active/<int:store_id>', methods=['POST'])
@admin_required
def toggle_store_active(store_id):
    if not current_user.brand_id or current_user.store_id:
        abort(403, description="매장 활성화/비활성화는 본사 관리자만 가능합니다.")
        
    try:
        store = Store.query.filter_by(
            id=store_id, 
            brand_id=current_user.current_brand_id
        ).first()
        if not store:
            return jsonify({'status': 'error', 'message': '매장을 찾을 수 없습니다.'}), 404
        
        store.is_active = not store.is_active
        db.session.commit()
        
        message = f"'{store.store_name}' 매장을 '활성' 상태로 변경했습니다." if store.is_active else f"'{store.store_name}' 매장을 '비활성' 상태로 변경했습니다. (소속 계정 로그인 불가)"
        return jsonify({'status': 'success', 'message': message, 'new_active_status': store.is_active})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling store active: {e}")
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500

@api_bp.route('/api/stores/reset/<int:store_id>', methods=['POST'])
@admin_required
def reset_store_registration(store_id):
    if not current_user.brand_id or current_user.store_id:
        abort(403, description="매장 등록 초기화는 본사 관리자만 가능합니다.")
        
    try:
        store = Store.query.filter_by(
            id=store_id, 
            brand_id=current_user.current_brand_id
        ).first()
        if not store:
            return jsonify({'status': 'error', 'message': '매장을 찾을 수 없습니다.'}), 404

        users_to_delete = User.query.filter_by(store_id=store.id).all()
        user_count = len(users_to_delete)
        for user in users_to_delete:
            db.session.delete(user)
            
        store.manager_name = None
        store.is_registered = False
        store.is_approved = False
        store.is_active = True 
        
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': f"'{store.store_name}' 매장의 등록 정보가 초기화되었습니다. (연결된 계정 {user_count}개 삭제됨)"})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error resetting store: {e}")
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500

@api_bp.route('/api/brands/<int:brand_id>/unregistered_stores', methods=['GET'])
def get_unregistered_stores_by_brand(brand_id):
    try:
        stores = Store.query.filter_by(
            brand_id=brand_id,
            is_registered=False, 
            is_active=True       
        ).order_by(Store.store_name).all()
        
        stores_list = [{
            'id': s.id,
            'name': s.store_name,
            'code': s.store_code
        } for s in stores]
        
        return jsonify({'status': 'success', 'stores': stores_list})
        
    except Exception as e:
        print(f"Error getting unregistered stores: {e}")
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500


@api_bp.route('/api/staff', methods=['POST'])
@admin_required
def add_staff():
    if not current_user.store_id:
        abort(403, description="직원 관리는 매장 관리자만 가능합니다.")
    data = request.json
    name = data.get('name', '').strip()
    position = data.get('position', '').strip()
    contact = data.get('contact', '').strip()
    if not name:
        return jsonify({'status': 'error', 'message': '직원 이름은 필수입니다.'}), 400
    try:
        new_staff = Staff(
            store_id=current_user.store_id,
            name=name,
            position=position or None,
            contact=contact or None,
            is_active=True
        )
        db.session.add(new_staff)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f"직원 '{name}'(이)가 추가되었습니다.",
            'staff': {
                'id': new_staff.id, 
                'name': new_staff.name,
                'position': new_staff.position or '',
                'contact': new_staff.contact or ''
            }
        }), 201 
    except Exception as e:
        db.session.rollback()
        print(f"Error adding staff: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500

@api_bp.route('/api/staff/<int:staff_id>', methods=['POST'])
@admin_required
def update_staff(staff_id):
    if not current_user.store_id:
        abort(403, description="직원 관리는 매장 관리자만 가능합니다.")
    data = request.json
    name = data.get('name', '').strip()
    position = data.get('position', '').strip()
    contact = data.get('contact', '').strip()
    if not name:
         return jsonify({'status': 'error', 'message': '직원 이름은 필수입니다.'}), 400
    try:
        staff = Staff.query.filter_by(
            id=staff_id, 
            store_id=current_user.store_id
        ).first()
        if not staff:
            return jsonify({'status': 'error', 'message': '수정할 직원을 찾을 수 없습니다.'}), 404
        staff.name = name
        staff.position = position or None
        staff.contact = contact or None
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f"'{name}' 직원 정보가 수정되었습니다.",
            'staff': {
                'id': staff.id, 
                'name': staff.name,
                'position': staff.position or '',
                'contact': staff.contact or ''
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating staff: {e}")
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500

@api_bp.route('/api/staff/<int:staff_id>', methods=['DELETE'])
@admin_required
def delete_staff(staff_id):
    if not current_user.store_id:
        abort(403, description="직원 관리는 매장 관리자만 가능합니다.")
    try:
        staff = Staff.query.filter_by(
            id=staff_id, 
            store_id=current_user.store_id
        ).first()
        if not staff:
            return jsonify({'status': 'error', 'message': '삭제할 직원을 찾을 수 없습니다.'}), 404
        name = staff.name
        staff.is_active = False 
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f"'{name}' 직원이 (비활성) 삭제 처리되었습니다."
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting staff: {e}")
        return jsonify({'status': 'error', 'message': f'서버 오류: {e}'}), 500

@api_bp.route('/api/reset-orders-db', methods=['POST'])
@admin_required
def reset_orders_db():
    if not current_user.store_id:
        abort(403, description="주문 DB 초기화는 매장 관리자만 가능합니다.")

    try:
        engine = db.get_engine(bind=None)
        if engine is None:
            raise Exception("Default bind engine not found.")

        print("Deleting 'orders' bind tables...")
        
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

        print("Deleting 'announcements' bind table...")
        
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

        print("Deleting 'store_info' bind table...")
        
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
        print("Deleting Product/Variant/StoreStock/Sales tables...")
        engine = db.get_engine(bind=None)
        
        # [수정] SaleItem, Sale을 목록에 추가 (참조 역순으로 삭제)
        tables_to_drop = [
            SaleItem.__table__,
            Sale.__table__,
            StoreStock.__table__, 
            Variant.__table__, 
            Product.__table__
        ]
        
        db.Model.metadata.drop_all(bind=engine, tables=tables_to_drop, checkfirst=True)
        db.Model.metadata.create_all(bind=engine, tables=tables_to_drop, checkfirst=True)
        
        flash('상품 데이터 초기화 완료. (상품/옵션/재고/매출 데이터 삭제됨. 계정/주문 내역 보존)', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'DB 초기화 오류: {e}', 'error')
        print(f"DB Reset Error: {e}")
        traceback.print_exc()
    return redirect(url_for('ui.setting_page'))