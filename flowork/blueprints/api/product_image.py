import uuid
import threading
import traceback
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import text, func, or_, case
from flowork.models import db, Product, Variant
from . import api_bp
from .tasks import TASKS, run_async_image_process

@api_bp.route('/api/product/images', methods=['GET'])
@login_required
def get_product_image_status():
    if not current_user.brand_id:
        return jsonify({'status': 'error', 'message': '브랜드 계정이 필요합니다.'}), 403

    try:
        # 1. 파라미터 수신 (페이지네이션 및 필터)
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        tab_type = request.args.get('tab', 'all') # processing, failed, completed, all
        search_query = request.args.get('query', '').strip()

        # 2. 기본 쿼리 구성 (Product + Variant 조인하여 컬러 수 계산)
        # SQL Group By를 사용하여 사이즈 중복을 DB단에서 제거하고 컬러 수만 셉니다.
        query = db.session.query(
            Product.product_number,
            Product.product_name,
            Product.image_status,
            Product.thumbnail_url,
            Product.detail_image_url,
            Product.image_drive_link,
            Product.last_message,
            func.count(func.distinct(Variant.color)).label('total_colors')
        ).outerjoin(Variant, Product.id == Variant.product_id)\
         .filter(Product.brand_id == current_user.current_brand_id)\
         .group_by(Product.id)

        # 3. 탭별 필터링 적용
        if tab_type == 'processing':
            # 진행중 또는 대기 상태
            query = query.filter(or_(
                Product.image_status == 'PROCESSING',
                Product.image_status == 'READY',
                Product.image_status == None
            ))
        elif tab_type == 'failed':
            query = query.filter(Product.image_status == 'FAILED')
        elif tab_type == 'completed':
            query = query.filter(Product.image_status == 'COMPLETED')
        
        # 4. 검색 필터링 (품번 또는 품명)
        if search_query:
            search_term = f"%{search_query.upper()}%"
            query = query.filter(or_(
                Product.product_number.ilike(search_term),
                Product.product_name.ilike(search_term)
            ))

        # 5. 정렬 및 페이지네이션 (DB에서 자름)
        # 우선순위: 진행중/실패가 상단, 나머지는 품번순
        pagination = query.order_by(
            case(
                (Product.image_status == 'PROCESSING', 1),
                (Product.image_status == 'FAILED', 2),
                else_=3
            ),
            Product.product_number.asc()
        ).paginate(page=page, per_page=limit, error_out=False)

        # 6. 결과 변환
        result_list = []
        for row in pagination.items:
            # row는 튜플 형태: (product_number, product_name, ..., total_colors)
            item = {
                'style_code': row.product_number,
                'product_name': row.product_name,
                'status': row.image_status or 'READY',
                'thumbnail': row.thumbnail_url,
                'detail': row.detail_image_url,
                'drive_link': row.image_drive_link,
                'message': row.last_message,
                'total_colors': row.total_colors # DB에서 계산된 컬러 수
            }
            result_list.append(item)

        return jsonify({
            'status': 'success', 
            'data': result_list,
            'pagination': {
                'current_page': pagination.page,
                'total_pages': pagination.pages,
                'total_items': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })

    except Exception as e:
        print(f"⚠️ DB 조회 중 오류: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'DB 조회 오류: {str(e)}'}), 500

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
        for code in style_codes:
            db.session.query(Product).filter(
                Product.brand_id == current_user.current_brand_id,
                Product.product_number.like(f"{code}%")
            ).update({
                Product.image_status: 'PROCESSING',
                Product.last_message: '작업 시작됨...'
            }, synchronize_session=False)
            
        db.session.commit()

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
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/product/images/reset', methods=['POST'])
@login_required
def reset_image_process_status():
    if not current_user.brand_id:
         return jsonify({'status': 'error', 'message': '권한이 없습니다.'}), 403

    data = request.json
    style_codes = data.get('style_codes', [])

    if not style_codes:
        return jsonify({'status': 'error', 'message': '선택된 품번이 없습니다.'}), 400

    try:
        updated_count = 0
        for code in style_codes:
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