import json
from flask import render_template, abort
from flask_login import login_required, current_user
from flowork.models import db, Brand, Store, Staff, Setting
from flowork.modules.admin import admin_bp

@admin_bp.route('/setting')
@login_required
def setting_page():
    if not current_user.is_admin and not current_user.is_super_admin: abort(403)
    
    bid = current_user.current_brand_id
    sid = current_user.store_id
    
    b_name = "FLOWORK (Super Admin)"
    stores = []
    staffs = []
    cat_conf = None
    exp_file = None
    load_file = None
    
    if bid:
        b = db.session.get(Brand, bid)
        s = Setting.query.filter_by(brand_id=bid, key='BRAND_NAME').first()
        b_name = (s.value if s else b.brand_name) or "No Name"
        stores = Store.query.filter_by(brand_id=bid).order_by(Store.store_name).all()
        
        if not sid:
            c_set = Setting.query.filter_by(brand_id=bid, key='CATEGORY_CONFIG').first()
            if c_set:
                try: cat_conf = json.loads(c_set.value)
                except: pass
            if b: exp_file = f"{b.brand_name}.json"
            l_set = Setting.query.filter_by(brand_id=bid, key='LOADED_SETTINGS_FILE').first()
            if l_set: load_file = l_set.value
            
    if sid:
        staffs = Staff.query.filter_by(store_id=sid, is_active=True).order_by(Staff.name).all()
        
    return render_template('setting.html', active_page='setting', brand_name=b_name,
                           my_store_id=sid, all_stores=stores, staff_list=staffs,
                           category_config=cat_conf, expected_settings_file=exp_file,
                           loaded_settings_file=load_file)

@admin_bp.route('/schedule')
@login_required
def schedule():
    if not current_user.store_id: abort(403)
    staff_list = Staff.query.filter_by(store_id=current_user.store_id, is_active=True).order_by(Staff.name).all()
    return render_template('schedule.html', active_page='schedule', staff_list=staff_list)