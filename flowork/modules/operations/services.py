from flowork.models import db, Attendance, CompetitorBrand, CompetitorSale, Staff
from datetime import datetime

def get_attendance_data(store_id, date_obj):
    staffs = Staff.query.filter_by(store_id=store_id, is_active=True).all()
    atts = {a.staff_id: a for a in Attendance.query.filter_by(store_id=store_id, work_date=date_obj).all()}
    res = []
    for s in staffs:
        a = atts.get(s.id)
        res.append({
            'staff_id': s.id, 'name': s.name, 'position': s.position,
            'status': a.status if a else '출근',
            'check_in': a.check_in_time.strftime('%H:%M') if a and a.check_in_time else '',
            'check_out': a.check_out_time.strftime('%H:%M') if a and a.check_out_time else '',
            'memo': a.memo if a else ''
        })
    return res

def save_attendance_data(store_id, date_obj, records):
    try:
        for r in records:
            sid = r['staff_id']
            att = Attendance.query.filter_by(store_id=store_id, staff_id=sid, work_date=date_obj).first()
            if not att:
                att = Attendance(store_id=store_id, staff_id=sid, work_date=date_obj)
                db.session.add(att)
            
            att.status = r.get('status', '출근')
            att.memo = r.get('memo', '')
            it, ot = r.get('check_in'), r.get('check_out')
            att.check_in_time = datetime.strptime(it, '%H:%M').time() if it else None
            att.check_out_time = datetime.strptime(ot, '%H:%M').time() if ot else None
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def get_comp_sales_data(store_id, date_obj):
    brands = CompetitorBrand.query.filter_by(store_id=store_id, is_active=True).all()
    sales = {s.competitor_id: s for s in CompetitorSale.query.filter_by(store_id=store_id, sale_date=date_obj).all()}
    res = []
    for b in brands:
        s = sales.get(b.id)
        res.append({
            'brand_id': b.id, 'brand_name': b.name,
            'off_norm': s.offline_normal if s else 0, 'off_evt': s.offline_event if s else 0,
            'on_norm': s.online_normal if s else 0, 'on_evt': s.online_event if s else 0
        })
    return res