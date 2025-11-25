import json
import os
import traceback
from flask import request, jsonify, current_app, flash, redirect, url_for, abort
from flask_login import login_required, current_user, logout_user
from sqlalchemy import func, exc

# [신규] UpdateLog 모델 추가
from flowork.models import db, Brand, Store, Setting, User, Staff, Sale, StockHistory, UpdateLog
# [신규] 버전 관리 서비스 추가
from flowork.services.version_service import VersionService
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

@api_bp.route('/api/setting/logo', methods=['POST'])
@admin_required
def upload_brand_logo():
    if not current_user.brand_id or current_user.store_id:
        return jsonify({'status': 'error', 'message': '본사 관리자만 로고를 설정할 수 있습니다.'}), 403

    if 'logo_file' not in request.files:
        return jsonify({'status': 'error', 'message': '파일이 없습니다.'}), 400
        
    file = request.files['logo_file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '선택된 파일이 없습니다.'}), 400

    try:
        static_folder = os.path.join(current_app.root_path, 'static', 'product_images')
        os.makedirs(static_folder, exist_ok=True)
        
        file_path = os.path.join(static_folder, 'thumbnail_logo.png')
        file.save(file_path)
        
        return jsonify({'status': 'success', 'message': '썸네일용 로고가 성공적으로 업로드되었습니다.'})
        
    except Exception as e:
        print(f"Logo upload error: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'로고 저장 실패: {e}'}), 500

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
            
        loaded_status_key = 'LOADED_SETTINGS_FILE'
        setting = Setting.query.filter_by(brand_id=brand.id, key=loaded_status_key).first()
        if setting:
            setting.value = filename
        else:
            new_setting = Setting(brand_id=brand.id, key=loaded_status_key, value=filename)
            db.session.add(new_setting)
                
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


@api_bp.route('/api/stores/<int:store_id>', methods=['DELETE', 'POST'])
@login_required
def delete_store(store_id):
    is_hq_admin = current_user.brand_id and not current_user.store_id
    is_store_self_delete = current_user.store_id and current_user.store_id == store_id
    is_super_admin = current_user.is_super_admin

    if not (is_hq_admin or is_store_self_delete or is_super_admin):
        abort(403, description="삭제 권한이 없습니다.")

    try:
        if is_store_self_delete:
            store = Store.query.filter_by(id=store_id, brand_id=current_user.brand_id).first()
        else:
            if is_hq_admin:
                store = Store.query.filter_by(id=store_id, brand_id=current_user.current_brand_id).first()
            else: 
                store = db.session.get(Store, store_id)
        
        if not store:
            if request.method == 'POST':
                flash('삭제할 매장을 찾을 수 없습니다.', 'error')
                return redirect(url_for('ui.setting_page'))
            return jsonify({'status': 'error', 'message': '삭제할 매장을 찾을 수 없습니다.'}), 404
        
        if is_hq_admin and store.is_registered:
            msg = f"'{store.store_name}'(은)는 가입된 매장입니다. 계정 삭제는 '등록 초기화' 기능을 사용하세요."
            if request.method == 'POST':
                flash(msg, 'error')
                return redirect(url_for('ui.setting_page'))
            return jsonify({'status': 'error', 'message': msg}), 403

        name = store.store_name
        db.session.delete(store)
        db.session.commit()
        
        if is_store_self_delete:
            logout_user()
            flash(f"매장 계정({name})이 삭제되었습니다.", 'info')
            return redirect(url_for('auth.login'))

        if request.method == 'POST':
            flash(f"'{name}' 매장이 삭제되었습니다.", 'success')
            return redirect(url_for('ui.setting_page'))
        
        return jsonify({
            'status': 'success',
            'message': f"'{name}'(이)가 삭제되었습니다."
        })
        
    except exc.IntegrityError:
        db.session.rollback()
        msg = f"'{name}'(은)는 현재 주문/재고 내역에서 사용 중이므로 삭제할 수 없습니다."
        if request.method == 'POST':
            flash(msg, 'error')
            return redirect(url_for('ui.setting_page'))
        return jsonify({'status': 'error', 'message': msg}), 409
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting store: {e}")
        if request.method == 'POST':
            flash(f"서버 오류: {e}", 'error')
            return redirect(url_for('ui.setting_page'))
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
        
        user_ids = [u.id for u in users_to_delete]
        if user_ids:
            db.session.query(Sale).filter(Sale.user_id.in_(user_ids)).update({Sale.user_id: None}, synchronize_session=False)
            
            db.session.query(StockHistory).filter(StockHistory.user_id.in_(user_ids)).update({StockHistory.user_id: None}, synchronize_session=False)

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

# [신규] 시스템 로그 조회 API
@api_bp.route('/api/system/logs', methods=['GET'])
@login_required
def get_update_logs():
    logs = UpdateLog.query.order_by(UpdateLog.created_at.desc()).all()
    data = [{
        'version': log.version,
        'title': log.title,
        'content': log.content,
        'date': log.created_at.strftime('%Y-%m-%d %H:%M'),
        'admin': log.created_by.username if log.created_by else 'System'
    } for log in logs]
    return jsonify({'status': 'success', 'logs': data})

# [신규] 시스템 로그 자동 생성 API
@api_bp.route('/api/system/logs/auto', methods=['POST'])
@admin_required
def create_auto_log():
    result = VersionService.generate_auto_log(current_user.id)
    return jsonify(result)