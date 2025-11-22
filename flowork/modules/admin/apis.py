import io
import os
import json
from datetime import datetime
from flask import request, jsonify, send_file, current_app, flash, redirect, url_for
from flask_login import login_required, current_user, logout_user
from flowork.modules.admin import admin_bp
from flowork.modules.admin.services import *
from flowork.models import Setting, db, Store, ScheduleEvent

# --- 브랜드/설정 관련 ---

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

@admin_bp.route('/api/setting/logo', methods=['POST'])
@login_required
def api_upload_logo():
    if not current_user.brand_id or current_user.store_id: return jsonify({'status':'error'}), 403
    f = request.files.get('logo_file')
    if not f: return jsonify({'status':'error'}), 400
    path = os.path.join(current_app.root_path, 'static', 'logo.png')
    f.save(path)
    return jsonify({'status':'success', 'message':'로고 저장 완료'})


# --- 매장 관리 ---

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
    if current_user.store_id and current_user.store_id == sid: 
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


# --- 직원 관리 ---

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


# --- 유지보수 (Export/Import/Reset) ---

@admin_bp.route('/api/maintenance/export_stores', methods=['GET'])
@login_required
def api_export_stores():
    if current_user.store_id: return abort(403)
    df = export_stores_service(current_user.current_brand_id)
    if df is None: return redirect(url_for('admin.setting_page'))
    
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    out.seek(0)
    return send_file(out, as_attachment=True, download_name=f"stores_backup_{datetime.now().strftime('%Y%m%d')}.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@admin_bp.route('/api/maintenance/import_stores', methods=['POST'])
@login_required
def api_import_stores():
    if current_user.store_id: return abort(403)
    f = request.files.get('excel_file')
    if not f: return redirect(url_for('admin.setting_page'))
    ok, msg = import_stores_service(f, current_user.current_brand_id)
    flash(msg, 'success' if ok else 'error')
    return redirect(url_for('admin.setting_page'))

@admin_bp.route('/api/reset-store-db', methods=['POST'])
@login_required
def api_reset_system():
    if not current_user.is_super_admin: return abort(403)
    ok, msg = reset_all_system_db()
    flash(msg, 'success' if ok else 'error')
    return redirect(url_for('admin.setting_page'))


# --- 일정 관리 (Schedule) - [신규 추가] ---

@admin_bp.route('/api/schedule/events', methods=['GET'])
@login_required
def api_get_schedule_events():
    if not current_user.store_id: return jsonify([])
    
    start = request.args.get('start')
    end = request.args.get('end')
    
    q = ScheduleEvent.query.filter_by(store_id=current_user.store_id)
    if start: q = q.filter(ScheduleEvent.start_time >= datetime.fromisoformat(start))
    if end: q = q.filter(ScheduleEvent.start_time <= datetime.fromisoformat(end))
    
    events = q.all()
    return jsonify([{
        'id': e.id,
        'title': f"{e.title} ({e.staff.name})" if e.staff else e.title,
        'raw_title': e.title,
        'start': e.start_time.isoformat(),
        'end': e.end_time.isoformat() if e.end_time else None,
        'allDay': e.all_day,
        'color': e.color,
        'extendedProps': {
            'event_type': e.event_type,
            'staff_id': e.staff_id
        }
    } for e in events])

@admin_bp.route('/api/schedule/events', methods=['POST'])
@login_required
def api_add_schedule_event():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    data = request.json
    
    try:
        ev = ScheduleEvent(
            store_id=current_user.store_id,
            staff_id=int(data['staff_id']) if data.get('staff_id') and int(data['staff_id']) > 0 else None,
            title=data['title'],
            event_type=data['event_type'],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            all_day=data.get('all_day', True),
            color=data.get('color', '#3788d8')
        )
        db.session.add(ev)
        db.session.commit()
        return jsonify({'status':'success', 'message':'일정 등록 완료', 'id':ev.id})
    except Exception as e:
        return jsonify({'status':'error', 'message':str(e)}), 500

@admin_bp.route('/api/schedule/events/<int:event_id>', methods=['POST'])
@login_required
def api_update_schedule_event(event_id):
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    ev = ScheduleEvent.query.filter_by(id=event_id, store_id=current_user.store_id).first()
    if not ev: return jsonify({'status':'error', 'message':'일정 없음'}), 404
    
    data = request.json
    try:
        ev.staff_id = int(data['staff_id']) if data.get('staff_id') and int(data['staff_id']) > 0 else None
        ev.title = data['title']
        ev.event_type = data['event_type']
        ev.start_time = datetime.fromisoformat(data['start_time'])
        ev.end_time = datetime.fromisoformat(data['end_time']) if data.get('end_time') else None
        ev.all_day = data.get('all_day', True)
        ev.color = data.get('color', '#3788d8')
        
        db.session.commit()
        return jsonify({'status':'success', 'message':'일정 수정 완료'})
    except Exception as e:
        return jsonify({'status':'error', 'message':str(e)}), 500

@admin_bp.route('/api/schedule/events/<int:event_id>', methods=['DELETE'])
@login_required
def api_delete_schedule_event(event_id):
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    ev = ScheduleEvent.query.filter_by(id=event_id, store_id=current_user.store_id).first()
    if not ev: return jsonify({'status':'error', 'message':'일정 없음'}), 404
    
    db.session.delete(ev)
    db.session.commit()
    return jsonify({'status':'success', 'message':'일정 삭제 완료'})