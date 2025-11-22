import io
import os
from datetime import datetime
from flask import request, jsonify, send_file, current_app, flash, redirect, url_for
from flask_login import login_required, current_user, logout_user
from flowork.modules.admin import admin_bp
from flowork.modules.admin.services import *
from flowork.models import Setting, db, Store

@admin_bp.route('/api/setting/brand_name', methods=['POST'])
@login_required
def api_update_brand_name():
    if not current_user.brand_id or current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg = update_brand_name_service(current_user.current_brand_id, request.json.get('brand_name',''))
    if ok: return jsonify({'status':'success', 'message':msg, 'brand_name':request.json.get('brand_name')})
    return jsonify({'status':'error', 'message':msg}), 500

@admin_bp.route('/api/setting/load_from_file', methods=['POST'])
@login_required
def api_load_settings():
    if not current_user.brand_id or current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg = load_settings_file_service(current_user.current_brand_id)
    if ok: return jsonify({'status':'success', 'message':msg})
    return jsonify({'status':'error', 'message':msg}), 500

@admin_bp.route('/api/setting', methods=['POST'])
@login_required
def api_update_setting():
    if not current_user.brand_id or current_user.store_id: return jsonify({'status':'error'}), 403
    k, v = request.json.get('key'), request.json.get('value')
    if not k: return jsonify({'status':'error'}), 400
    
    val = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict,list)) else str(v)
    s = Setting.query.filter_by(brand_id=current_user.current_brand_id, key=k).first()
    if s: s.value = val
    else: db.session.add(Setting(brand_id=current_user.current_brand_id, key=k, value=val))
    db.session.commit()
    return jsonify({'status':'success', 'message':'저장됨'})

@admin_bp.route('/api/stores', methods=['GET'])
@login_required
def api_get_stores():
    stores = Store.query.filter_by(brand_id=current_user.current_brand_id).order_by(Store.store_name).all()
    return jsonify({'status':'success', 'stores':[{'id':s.id, 'store_code':s.store_code, 'store_name':s.store_name, 'phone_number':s.phone_number, 'manager_name':s.manager_name, 'is_registered':s.is_registered, 'is_approved':s.is_approved, 'is_active':s.is_active} for s in stores]})

@admin_bp.route('/api/stores', methods=['POST'])
@login_required
def api_add_store():
    if not current_user.brand_id or current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg, s = manage_store_service('create', current_user.current_brand_id, request.json)
    if ok: return jsonify({'status':'success', 'message':msg, 'store':{'id':s.id, 'store_code':s.store_code, 'store_name':s.store_name, 'phone_number':s.phone_number, 'manager_name':s.manager_name, 'is_registered':s.is_registered, 'is_approved':s.is_approved, 'is_active':s.is_active}}), 201
    return jsonify({'status':'error', 'message':msg}), 409

@admin_bp.route('/api/stores/<int:sid>', methods=['POST'])
@login_required
def api_update_store(sid):
    if not current_user.brand_id or current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg, s = manage_store_service('update', current_user.current_brand_id, request.json, sid)
    if ok: return jsonify({'status':'success', 'message':msg, 'store':{'id':s.id, 'store_code':s.store_code, 'store_name':s.store_name, 'phone_number':s.phone_number, 'manager_name':s.manager_name, 'is_registered':s.is_registered, 'is_approved':s.is_approved, 'is_active':s.is_active}})
    return jsonify({'status':'error', 'message':msg}), 500

@admin_bp.route('/api/stores/<int:sid>', methods=['DELETE'])
@login_required
def api_delete_store(sid):
    bid = current_user.brand_id
    if current_user.store_id and current_user.store_id == sid: # Self delete
        ok, msg, _ = manage_store_service('delete', bid, None, sid)
        if ok:
            logout_user()
            return jsonify({'status':'success', 'message':'계정 삭제됨'})
        return jsonify({'status':'error', 'message':msg}), 409
    
    if not bid or current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg, _ = manage_store_service('delete', bid, None, sid)
    if ok: return jsonify({'status':'success', 'message':msg})
    return jsonify({'status':'error', 'message':msg}), 409

@admin_bp.route('/api/stores/approve/<int:sid>', methods=['POST'])
@login_required
def api_approve_store(sid):
    if not current_user.brand_id or current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg, _ = manage_store_service('approve', current_user.current_brand_id, None, sid)
    if ok: return jsonify({'status':'success', 'message':msg})
    return jsonify({'status':'error', 'message':msg}), 500

@admin_bp.route('/api/stores/toggle_active/<int:sid>', methods=['POST'])
@login_required
def api_toggle_store(sid):
    if not current_user.brand_id or current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg, stat = manage_store_service('toggle', current_user.current_brand_id, None, sid)
    if ok: return jsonify({'status':'success', 'message':msg, 'new_active_status':stat})
    return jsonify({'status':'error', 'message':msg}), 500

@admin_bp.route('/api/stores/reset/<int:sid>', methods=['POST'])
@login_required
def api_reset_store(sid):
    if not current_user.brand_id or current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg, _ = manage_store_service('reset', current_user.current_brand_id, None, sid)
    if ok: return jsonify({'status':'success', 'message':msg})
    return jsonify({'status':'error', 'message':msg}), 500

@admin_bp.route('/api/staff', methods=['POST'])
@login_required
def api_add_staff():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg, st = manage_staff_service('create', current_user.store_id, request.json)
    if ok: return jsonify({'status':'success', 'message':msg, 'staff':{'id':st.id, 'name':st.name, 'position':st.position, 'contact':st.contact}}), 201
    return jsonify({'status':'error', 'message':msg}), 500

@admin_bp.route('/api/staff/<int:sid>', methods=['POST'])
@login_required
def api_update_staff(sid):
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg, st = manage_staff_service('update', current_user.store_id, request.json, sid)
    if ok: return jsonify({'status':'success', 'message':msg, 'staff':{'id':st.id, 'name':st.name, 'position':st.position, 'contact':st.contact}})
    return jsonify({'status':'error', 'message':msg}), 500

@admin_bp.route('/api/staff/<int:sid>', methods=['DELETE'])
@login_required
def api_delete_staff(sid):
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg, _ = manage_staff_service('delete', current_user.store_id, None, sid)
    if ok: return jsonify({'status':'success', 'message':msg})
    return jsonify({'status':'error', 'message':msg}), 500

@admin_bp.route('/api/maintenance/export_stores', methods=['GET'])
@login_required
def api_export_stores():
    if current_user.store_id: return abort(403)
    df = export_stores_service(current_user.current_brand_id)
    if df is None: return redirect(url_for('ui.setting_page'))
    
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    out.seek(0)
    return send_file(out, as_attachment=True, download_name=f"stores_backup_{datetime.now().strftime('%Y%m%d')}.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@admin_bp.route('/api/maintenance/import_stores', methods=['POST'])
@login_required
def api_import_stores():
    if current_user.store_id: return abort(403)
    f = request.files.get('excel_file')
    if not f: return redirect(url_for('ui.setting_page'))
    ok, msg = import_stores_service(f, current_user.current_brand_id)
    flash(msg, 'success' if ok else 'error')
    return redirect(url_for('ui.setting_page'))

@admin_bp.route('/api/reset-store-db', methods=['POST'])
@login_required
def api_reset_system():
    if not current_user.is_super_admin: return abort(403)
    ok, msg = reset_all_system_db()
    flash(msg, 'success' if ok else 'error')
    return redirect(url_for('ui.setting_page'))

@admin_bp.route('/api/setting/logo', methods=['POST'])
@login_required
def api_upload_logo():
    if not current_user.brand_id or current_user.store_id: return jsonify({'status':'error'}), 403
    f = request.files.get('logo_file')
    if not f: return jsonify({'status':'error'}), 400
    path = os.path.join(current_app.root_path, 'static', 'thumbnail_logo.png')
    f.save(path)
    return jsonify({'status':'success', 'message':'로고 저장 완료'})