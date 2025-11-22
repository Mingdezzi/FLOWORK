from flask import request, jsonify
from flask_login import login_required, current_user
from flowork.modules.auth import auth_bp
from flowork.modules.auth.services import change_user_password

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password_api():
    data = request.json
    current_pw = data.get('current_password')
    new_pw = data.get('new_password')
    
    if not current_pw or not new_pw:
        return jsonify({'status': 'error', 'message': '입력 값이 부족합니다.'}), 400
        
    success, msg = change_user_password(current_user, current_pw, new_pw)
    
    if success:
        return jsonify({'status': 'success', 'message': '비밀번호가 변경되었습니다.'})
    else:
        return jsonify({'status': 'error', 'message': msg}), 400