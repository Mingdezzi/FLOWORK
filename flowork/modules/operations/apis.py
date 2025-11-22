from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from flowork.modules.operations import operations_bp
from flowork.modules.operations.services import get_attendance_data, save_attendance_data, get_comp_sales_data
from flowork.models import db, CompetitorBrand, CompetitorSale

@operations_bp.route('/api/attendance', methods=['GET', 'POST'])
@login_required
def api_attendance():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    
    if request.method == 'GET':
        dt = request.args.get('date')
        if not dt: return jsonify({'status':'error'}), 400
        return jsonify({'status':'success', 'data': get_attendance_data(current_user.store_id, datetime.strptime(dt, '%Y-%m-%d').date())})
    else:
        d = request.json
        ok, msg = save_attendance_data(current_user.store_id, datetime.strptime(d['date'], '%Y-%m-%d').date(), d['records'])
        if ok: return jsonify({'status':'success', 'message':'저장 완료'})
        return jsonify({'status':'error', 'message':msg}), 500

@operations_bp.route('/api/competitor/brands', methods=['GET', 'POST'])
@login_required
def api_comp_brands():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    if request.method == 'GET':
        bs = CompetitorBrand.query.filter_by(store_id=current_user.store_id, is_active=True).all()
        return jsonify({'status':'success', 'brands':[{'id':b.id, 'name':b.name} for b in bs]})
    else:
        n = request.json.get('name')
        if not n: return jsonify({'status':'error'}), 400
        b = CompetitorBrand(store_id=current_user.store_id, name=n)
        db.session.add(b)
        db.session.commit()
        return jsonify({'status':'success', 'message':'추가 완료'})

@operations_bp.route('/api/competitor/brands/<int:bid>', methods=['DELETE'])
@login_required
def api_del_comp_brand(bid):
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    b = CompetitorBrand.query.filter_by(id=bid, store_id=current_user.store_id).first()
    if b:
        b.is_active = False
        db.session.commit()
    return jsonify({'status':'success'})

@operations_bp.route('/api/competitor/sales', methods=['GET', 'POST'])
@login_required
def api_comp_sales():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    if request.method == 'GET':
        dt = request.args.get('date')
        if not dt: return jsonify({'status':'error'}), 400
        return jsonify({'status':'success', 'data': get_comp_sales_data(current_user.store_id, datetime.strptime(dt, '%Y-%m-%d').date())})
    else:
        d = request.json
        dt = datetime.strptime(d['date'], '%Y-%m-%d').date()
        for r in d['records']:
            s = CompetitorSale.query.filter_by(store_id=current_user.store_id, competitor_id=r['brand_id'], sale_date=dt).first()
            if not s:
                s = CompetitorSale(store_id=current_user.store_id, competitor_id=r['brand_id'], sale_date=dt)
                db.session.add(s)
            s.offline_normal = int(r.get('off_norm',0))
            s.offline_event = int(r.get('off_evt',0))
            s.online_normal = int(r.get('on_norm',0))
            s.online_event = int(r.get('on_evt',0))
        db.session.commit()
        return jsonify({'status':'success', 'message':'저장 완료'})