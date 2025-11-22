import json
import os
import io
import pandas as pd
from flask import current_app
from flowork.models import db, Brand, Store, User, Staff, Setting, Sale, StockHistory, Announcement, ScheduleEvent
from sqlalchemy import func, delete

def update_brand_name_service(brand_id, new_name):
    try:
        brand = db.session.get(Brand, brand_id)
        if not brand: return False, "브랜드 없음"
        brand.brand_name = new_name
        
        setting = Setting.query.filter_by(brand_id=brand_id, key='BRAND_NAME').first()
        if not setting:
            setting = Setting(brand_id=brand_id, key='BRAND_NAME')
            db.session.add(setting)
        setting.value = new_name
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def load_settings_file_service(brand_id):
    try:
        brand = db.session.get(Brand, brand_id)
        path = os.path.join(current_app.root_path, 'brands', f'{brand.brand_name}.json')
        if not os.path.exists(path): return False, "설정 파일 없음"
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        cnt = 0
        for k, v in data.items():
            val = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            s = Setting.query.filter_by(brand_id=brand_id, key=k).first()
            if s: s.value = val
            else: db.session.add(Setting(brand_id=brand_id, key=k, value=val))
            cnt += 1
            
        ls = Setting.query.filter_by(brand_id=brand_id, key='LOADED_SETTINGS_FILE').first()
        fname = f'{brand.brand_name}.json'
        if ls: ls.value = fname
        else: db.session.add(Setting(brand_id=brand_id, key='LOADED_SETTINGS_FILE', value=fname))
        
        db.session.commit()
        return True, f"{cnt}개 설정 로드 완료"
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def manage_store_service(action, brand_id, store_data=None, store_id=None):
    try:
        if action == 'create':
            code, name = store_data.get('store_code'), store_data.get('store_name')
            if Store.query.filter(Store.brand_id==brand_id, Store.store_code==code).first(): return False, "코드 중복", None
            if Store.query.filter(Store.brand_id==brand_id, func.lower(Store.store_name)==func.lower(name)).first(): return False, "이름 중복", None
            
            s = Store(brand_id=brand_id, store_code=code, store_name=name, phone_number=store_data.get('store_phone'), is_registered=False, is_approved=False, is_active=True)
            db.session.add(s)
            db.session.commit()
            return True, "매장 추가 완료", s
            
        elif action == 'update':
            s = Store.query.filter_by(id=store_id, brand_id=brand_id).first()
            if not s: return False, "매장 없음", None
            
            code, name = store_data.get('store_code'), store_data.get('store_name')
            if Store.query.filter(Store.brand_id==brand_id, Store.store_code==code, Store.id!=store_id).first(): return False, "코드 중복", None
            if Store.query.filter(Store.brand_id==brand_id, func.lower(Store.store_name)==func.lower(name), Store.id!=store_id).first(): return False, "이름 중복", None
            
            s.store_code = code
            s.store_name = name
            s.phone_number = store_data.get('store_phone')
            db.session.commit()
            return True, "수정 완료", s
            
        elif action == 'delete':
            s = Store.query.filter_by(id=store_id, brand_id=brand_id).first()
            if not s: return False, "매장 없음", None
            if s.is_registered: return False, "가입된 매장은 초기화 후 삭제하세요", None
            db.session.delete(s)
            db.session.commit()
            return True, "삭제 완료", None
            
        elif action == 'approve':
            s = Store.query.filter_by(id=store_id, brand_id=brand_id).first()
            if not s: return False, "매장 없음", None
            s.is_approved = True
            s.is_active = True
            db.session.commit()
            return True, "승인 완료", None
            
        elif action == 'toggle':
            s = Store.query.filter_by(id=store_id, brand_id=brand_id).first()
            if not s: return False, "매장 없음", None
            s.is_active = not s.is_active
            db.session.commit()
            return True, f"상태 변경: {s.is_active}", s.is_active
            
        elif action == 'reset':
            s = Store.query.filter_by(id=store_id, brand_id=brand_id).first()
            if not s: return False, "매장 없음", None
            users = User.query.filter_by(store_id=s.id).all()
            uids = [u.id for u in users]
            if uids:
                db.session.query(Sale).filter(Sale.user_id.in_(uids)).update({Sale.user_id:None}, synchronize_session=False)
                db.session.query(StockHistory).filter(StockHistory.user_id.in_(uids)).update({StockHistory.user_id:None}, synchronize_session=False)
                for u in users: db.session.delete(u)
            s.manager_name = None
            s.is_registered = False
            s.is_approved = False
            s.is_active = True
            db.session.commit()
            return True, "초기화 완료", None
            
    except Exception as e:
        db.session.rollback()
        return False, str(e), None

def manage_staff_service(action, store_id, staff_data=None, staff_id=None):
    try:
        if action == 'create':
            st = Staff(store_id=store_id, name=staff_data['name'], position=staff_data.get('position'), contact=staff_data.get('contact'), is_active=True)
            db.session.add(st)
            db.session.commit()
            return True, "직원 추가 완료", st
        elif action == 'update':
            st = Staff.query.filter_by(id=staff_id, store_id=store_id).first()
            if not st: return False, "직원 없음", None
            st.name = staff_data['name']
            st.position = staff_data.get('position')
            st.contact = staff_data.get('contact')
            db.session.commit()
            return True, "수정 완료", st
        elif action == 'delete':
            st = Staff.query.filter_by(id=staff_id, store_id=store_id).first()
            if not st: return False, "직원 없음", None
            st.is_active = False
            db.session.commit()
            return True, "삭제(비활성) 완료", None
    except Exception as e:
        db.session.rollback()
        return False, str(e), None

def export_stores_service(brand_id):
    try:
        stores = Store.query.filter_by(brand_id=brand_id).all()
        data = []
        for s in stores:
            users = User.query.filter_by(store_id=s.id).all()
            data.append({
                'store_code': s.store_code, 'store_name': s.store_name, 'phone_number': s.phone_number,
                'manager_name': s.manager_name, 'is_active': 'Y' if s.is_active else 'N',
                'usernames': ",".join([u.username for u in users])
            })
        return pd.DataFrame(data)
    except: return None

def import_stores_service(file, brand_id):
    try:
        df = pd.read_excel(file).fillna('')
        cnt = 0
        for _, row in df.iterrows():
            code, name = str(row.get('store_code','')).strip(), str(row.get('store_name','')).strip()
            if not name: continue
            
            s = Store.query.filter_by(brand_id=brand_id, store_name=name).first()
            if not s and code: s = Store.query.filter_by(brand_id=brand_id, store_code=code).first()
            
            if not s:
                s = Store(brand_id=brand_id, store_code=code, store_name=name, phone_number=row.get('phone_number'),
                          manager_name=row.get('manager_name'), is_active=(row.get('is_active')=='Y'),
                          is_registered=True, is_approved=True)
                db.session.add(s)
                cnt += 1
            else:
                s.store_code = code
                s.phone_number = row.get('phone_number')
                s.manager_name = row.get('manager_name')
                s.is_active = (row.get('is_active')=='Y')
        db.session.commit()
        return True, f"{cnt}개 신규 등록"
    except Exception as e: return False, str(e)

def reset_all_system_db():
    try:
        eng = db.get_engine()
        tbls = [ScheduleEvent.__table__, Staff.__table__, Setting.__table__, User.__table__, Store.__table__, Brand.__table__]
        db.Model.metadata.drop_all(bind=eng, tables=tbls)
        db.Model.metadata.create_all(bind=eng, tables=tbls)
        return True, "전체 시스템 초기화 완료"
    except Exception as e: return False, str(e)