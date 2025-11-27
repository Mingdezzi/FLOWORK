from flask import Blueprint, request, jsonify
from backend.models import User, Store
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    brand_id = data.get('brand_id') # 브랜드 선택 로그인 지원

    query = User.query.filter_by(username=username)
    if brand_id:
        query = query.filter_by(brand_id=brand_id)
    
    user = query.first()

    # bcrypt 검증 (구현 생략, 실제로는 bcrypt.checkpw 사용)
    # 여기서는 데모용으로 단순 문자열 비교 혹은 hash 함수 사용
    if user and user.password_hash == password: # TODO: Real hash check
        token = create_access_token(identity=user.id)
        
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'store_id': user.store_id,
                'brand_id': user.brand_id
            }
        })
    
    return jsonify({'message': 'Invalid credentials'}), 401

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    store_name = user.store.name if user.store else 'Headquarters'
    return jsonify({
        'username': user.username,
        'role': user.role,
        'store_name': store_name
    })