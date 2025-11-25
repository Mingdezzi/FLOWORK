from datetime import datetime
from flask import request, jsonify
from flask_login import login_required, current_user
from flowork.models import db, Attendance, CompetitorBrand, CompetitorSale, Staff
from flowork.services.operations_service import OperationsService
from . import api_bp

# --- 근태 관리 API ---

@api_bp.route('/api/attendance', methods=['GET'])
@login_required
def get_attendance():
    if not current_user.store_id:
        return jsonify({'status': 'error', 'message': '매장 권한이 필요합니다.'}), 403
    
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'status': 'error', 'message': '날짜가 필요합니다.'}), 400
        
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # 해당 매장의 모든 직원 조회
    staffs = Staff.query.filter_by(store_id=current_user.store_id, is_active=True).all()
    
    # 해당 날짜의 근태 기록 조회
    attendances = Attendance.query.filter_by(
        store_id=current_user.store_id,
        work_date=target_date
    ).all()
    att_map = {a.staff_id: a for a in attendances}
    
    result = []
    for s in staffs:
        att = att_map.get(s.id)
        result.append({
            'staff_id': s.id,
            'name': s.name,
            'position': s.position,
            'status': att.status if att else '출근',
            'check_in': att.check_in_time.strftime('%H:%M') if att and att.check_in_time else '',
            'check_out': att.check_out_time.strftime('%H:%M') if att and att.check_out_time else '',
            'memo': att.memo if att else ''
        })
        
    return jsonify({'status': 'success', 'data': result})

@api_bp.route('/api/attendance', methods=['POST'])
@login_required
def save_attendance():
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
    
    data = request.json
    date_str = data.get('date')
    records = data.get('records', [])
    
    if not date_str or not records:
        return jsonify({'status': 'error', 'message': '데이터 누락'}), 400
        
    result = OperationsService.save_attendance(
        store_id=current_user.store_id,
        date_str=date_str,
        records=records
    )
    
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code


# --- 타사 매출 관리 API ---

@api_bp.route('/api/competitor/brands', methods=['GET', 'POST'])
@login_required
def manage_competitor_brands():
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
    
    if request.method == 'GET':
        brands = CompetitorBrand.query.filter_by(store_id=current_user.store_id, is_active=True).all()
        return jsonify({
            'status': 'success', 
            'brands': [{'id': b.id, 'name': b.name} for b in brands]
        })
        
    elif request.method == 'POST':
        name = request.json.get('name', '').strip()
        if not name: return jsonify({'status': 'error', 'message': '브랜드명 필수'}), 400
        
        result = OperationsService.add_competitor_brand(current_user.store_id, name)
        status_code = 200 if result['status'] == 'success' else 500
        return jsonify(result), status_code

@api_bp.route('/api/competitor/brands/<int:brand_id>', methods=['DELETE'])
@login_required
def delete_competitor_brand(brand_id):
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
    
    result = OperationsService.delete_competitor_brand(brand_id, current_user.store_id)
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code

@api_bp.route('/api/competitor/sales', methods=['GET'])
@login_required
def get_competitor_sales():
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
    
    date_str = request.args.get('date')
    if not date_str: return jsonify({'status': 'error'}), 400
    
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    brands = CompetitorBrand.query.filter_by(store_id=current_user.store_id, is_active=True).all()
    sales = CompetitorSale.query.filter_by(store_id=current_user.store_id, sale_date=target_date).all()
    
    sale_map = {s.competitor_id: s for s in sales}
    
    result = []
    for b in brands:
        s = sale_map.get(b.id)
        result.append({
            'brand_id': b.id,
            'brand_name': b.name,
            'off_norm': s.offline_normal if s else 0,
            'off_evt': s.offline_event if s else 0,
            'on_norm': s.online_normal if s else 0,
            'on_evt': s.online_event if s else 0
        })
        
    return jsonify({'status': 'success', 'data': result})

@api_bp.route('/api/competitor/sales', methods=['POST'])
@login_required
def save_competitor_sales():
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
    
    data = request.json
    date_str = data.get('date')
    records = data.get('records', [])
    
    if not date_str: return jsonify({'status': 'error'}), 400
    
    result = OperationsService.save_competitor_sales(
        store_id=current_user.store_id,
        date_str=date_str,
        records=records
    )
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code