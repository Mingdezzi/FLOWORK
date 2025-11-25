from flask import request, jsonify, abort
from flask_login import login_required, current_user
from flowork.services.network_service import NetworkService
from . import api_bp

@api_bp.route('/api/suggestions', methods=['POST'])
@login_required
def create_suggestion():
    data = request.json
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    is_private = data.get('is_private', False)
    
    if not title or not content:
        return jsonify({'status': 'error', 'message': '제목과 내용은 필수입니다.'}), 400
        
    result = NetworkService.create_suggestion(
        brand_id=current_user.current_brand_id,
        store_id=current_user.store_id,
        title=title,
        content=content,
        is_private=is_private
    )
    
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code

@api_bp.route('/api/suggestions/<int:s_id>/comment', methods=['POST'])
@login_required
def add_suggestion_comment(s_id):
    content = request.json.get('content', '').strip()
    if not content: return jsonify({'status': 'error', 'message': '내용 없음'}), 400
    
    result = NetworkService.add_comment(
        suggestion_id=s_id,
        user_id=current_user.id,
        content=content
    )
    
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code

@api_bp.route('/api/suggestions/<int:s_id>', methods=['DELETE'])
@login_required
def delete_suggestion(s_id):
    result = NetworkService.delete_suggestion(
        suggestion_id=s_id,
        brand_id=current_user.current_brand_id,
        user=current_user
    )
    
    status_code = 200 if result['status'] == 'success' else 403 
    
    if result['status'] == 'error' and '권한' in result['message']:
        status_code = 403
    elif result['status'] == 'error' and '없음' in result['message']:
        status_code = 404
        
    return jsonify(result), status_code

@api_bp.route('/api/mails', methods=['POST'])
@login_required
def send_mail():
    data = request.json
    target_store_id = data.get('target_store_id') 
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    
    if not title or not content:
        return jsonify({'status': 'error', 'message': '제목/내용 필수'}), 400
    
    result = NetworkService.send_mail(
        brand_id=current_user.current_brand_id,
        sender_store_id=current_user.store_id,
        target_store_id=target_store_id,
        title=title,
        content=content
    )
    
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code

@api_bp.route('/api/mails/<int:m_id>', methods=['DELETE'])
@login_required
def delete_mail(m_id):
    result = NetworkService.delete_mail(
        mail_id=m_id,
        brand_id=current_user.current_brand_id,
        user_store_id=current_user.store_id
    )
    
    status_code = 200 if result['status'] == 'success' else 403
    return jsonify(result), status_code