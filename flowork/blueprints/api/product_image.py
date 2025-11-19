import uuid
import threading
import traceback
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import text
from sqlalchemy.orm import selectinload
from flowork.models import db, Product
from . import api_bp
from .tasks import TASKS, run_async_image_process

@api_bp.route('/api/product/images', methods=['GET'])
@login_required
def get_product_image_status():
    if not current_user.brand_id:
        return jsonify({'status': 'error', 'message': '브랜드 계정이 필요합니다.'}), 403

    try:
        # 1. 상품 및 옵션 정보 로드
        products = Product.query.options(selectinload(Product.variants))\
            .filter_by(brand_id=current_user.current_brand_id).all()
        
        groups = {}
        for p in products:
            style_code = p.product_number
            
            if style_code not in groups:
                groups[style_code] = {
                    'style_code': style_code,
                    'product_name': p.product_name,
                    'total_colors': 0,
                    'status': 'READY',
                    'thumbnail': None,
                    'detail': None,
                    'message': ''
                }
            
            group = groups[style_code]
            unique_colors = set(v.color for v in p.variants if v.color)
            group['total_colors'] = len(unique_colors) if unique_colors else 1
            
            _update_group_status_and_links(group, p)

    except Exception as e:
        print(f"⚠️ DB 조회 중 오류: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'DB 조회 오류: {str(e)}'}), 500

    # 리스트 변환 및 정렬
    result_list = list(groups.values())
    result_list.sort(key=lambda x: x['style_code'])

    return jsonify({'status': 'success', 'data': result_list})

def _update_group_status_and_links(group, product):
    """그룹 상태 및 정보 최신화"""
    current_status = group['status']
    item_status = product.image_status or 'READY'
    
    # 상태 우선순위: PROCESSING > FAILED > COMPLETED > READY
    if item_status == 'PROCESSING' or current_status == 'PROCESSING':
        group['status'] = 'PROCESSING'
    elif item_status == 'FAILED' and current_status != 'PROCESSING':
        group['status'] = 'FAILED'
    elif item_status == 'COMPLETED' and current_status == 'READY':
        group['status'] = 'COMPLETED'
        
    if product.thumbnail_url and not group['thumbnail']:
        group['thumbnail'] = product.thumbnail_url
    if product.detail_image_url and not group['detail']:
        group['detail'] = product.detail_image_url
        
    if product.last_message:
        if item_status == 'FAILED':
            group['message'] = product.last_message
        elif not group['message']:
            group['message'] = product.last_message

@api_bp.route('/api/product/images/process', methods=['POST'])
@login_required
def trigger_image_process():
    if not current_user.brand_id:
         return jsonify({'status': 'error', 'message': '권한이 없습니다.'}), 403
         
    data = request.json
    style_codes = data.get('style_codes', [])
    
    if not style_codes:
        return jsonify({'status': 'error', 'message': '선택된 품번이 없습니다.'}), 400

    try:
        # 1. Bulk Update: 선택된 품번들의 상태를 PROCESSING으로 변경
        for code in style_codes:
            db.session.query(Product).filter(
                Product.brand_id == current_user.current_brand_id,
                Product.product_number.like(f"{code}%")
            ).update({
                Product.image_status: 'PROCESSING',
                Product.last_message: '작업 시작됨...'
            }, synchronize_session=False)
            
        db.session.commit()

        # 2. 비동기 작업 시작
        task_id = str(uuid.uuid4())
        TASKS[task_id] = {
            'status': 'processing', 
            'current': 0, 
            'total': len(style_codes), 
            'percent': 0
        }
        
        thread = threading.Thread(
            target=run_async_image_process,
            args=(
                current_app._get_current_object(),
                task_id,
                current_user.current_brand_id,
                style_codes
            )
        )
        thread.start()

        return jsonify({
            'status': 'success', 
            'message': '이미지 처리가 시작되었습니다.', 
            'task_id': task_id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/product/images/reset', methods=['POST'])
@login_required
def reset_image_process_status():
    """선택한 품번의 상태를 'READY'로 강제 초기화 (Bulk Update 적용)"""
    if not current_user.brand_id:
         return jsonify({'status': 'error', 'message': '권한이 없습니다.'}), 403

    data = request.json
    style_codes = data.get('style_codes', [])

    if not style_codes:
        return jsonify({'status': 'error', 'message': '선택된 품번이 없습니다.'}), 400

    try:
        updated_count = 0
        for code in style_codes:
            # LIKE 쿼리로 해당 품번으로 시작하는 모든 상품 업데이트
            res = db.session.query(Product).filter(
                Product.brand_id == current_user.current_brand_id,
                Product.product_number.like(f"{code}%")
            ).update({
                Product.image_status: 'READY',
                Product.last_message: '사용자에 의해 초기화됨'
            }, synchronize_session=False)
            updated_count += res
            
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'{updated_count}개 상품의 상태를 초기화했습니다.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/product/images/reset_all_processing', methods=['POST'])
@login_required
def reset_all_processing_status():
    """'진행중(PROCESSING)' 상태인 모든 항목을 'READY'로 강제 초기화"""
    if not current_user.brand_id:
         return jsonify({'status': 'error', 'message': '권한이 없습니다.'}), 403

    try:
        res = db.session.query(Product).filter(
            Product.brand_id == current_user.current_brand_id,
            Product.image_status == 'PROCESSING'
        ).update({
            Product.image_status: 'READY',
            Product.last_message: '일괄 초기화됨'
        }, synchronize_session=False)
        
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'진행 중이던 {res}개 상품을 모두 대기 상태로 초기화했습니다.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
