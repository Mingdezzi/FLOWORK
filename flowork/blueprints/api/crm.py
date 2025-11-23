import traceback
from datetime import datetime
from flask import request, jsonify
from flask_login import login_required, current_user
from flowork.models import db, Customer, Repair
from flowork.services.crm_service import CrmService
from . import api_bp

# --- 고객 관리 API ---

@api_bp.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    if not current_user.store_id:
        return jsonify({'status': 'error', 'message': '매장 권한이 필요합니다.'}), 403
        
    query = request.args.get('query', '').strip()
    page = request.args.get('page', 1, type=int)
    
    base_query = Customer.query.filter_by(store_id=current_user.store_id)
    
    if query:
        base_query = base_query.filter(
            (Customer.name.contains(query)) | (Customer.phone.contains(query))
        )
        
    pagination = base_query.order_by(Customer.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    customers = [{
        'id': c.id,
        'code': c.customer_code,
        'name': c.name,
        'phone': c.phone,
        'address': c.address or '',
        'created_at': c.created_at.strftime('%Y-%m-%d')
    } for c in pagination.items]
    
    return jsonify({
        'status': 'success',
        'customers': customers,
        'total_pages': pagination.pages,
        'current_page': page
    })

@api_bp.route('/api/customers', methods=['POST'])
@login_required
def add_customer():
    if not current_user.store_id:
        return jsonify({'status': 'error', 'message': '매장 권한이 필요합니다.'}), 403
        
    data = request.json
    name = data.get('name')
    phone = data.get('phone')
    
    if not name or not phone:
        return jsonify({'status': 'error', 'message': '이름과 연락처는 필수입니다.'}), 400
        
    result = CrmService.add_customer(
        store_id=current_user.store_id,
        name=name,
        phone=phone,
        address=data.get('address')
    )
    
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code

# --- 수선 관리 API ---

@api_bp.route('/api/repairs', methods=['POST'])
@login_required
def add_repair():
    if not current_user.store_id:
        return jsonify({'status': 'error', 'message': '매장 권한이 필요합니다.'}), 403
        
    result = CrmService.create_repair(
        store_id=current_user.store_id,
        data=request.json
    )
    
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code

@api_bp.route('/api/repairs/<int:repair_id>/status', methods=['POST'])
@login_required
def update_repair_status(repair_id):
    if not current_user.store_id:
        return jsonify({'status': 'error'}), 403
        
    new_status = request.json.get('status')
    if not new_status:
        return jsonify({'status': 'error', 'message': '상태 값 누락'}), 400
        
    result = CrmService.update_repair_status(
        repair_id=repair_id,
        store_id=current_user.store_id,
        new_status=new_status
    )
    
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code