import uuid
import threading
import traceback
import os
import io
import shutil
import zipfile
from flask import request, jsonify, current_app, send_file
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
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        tab_type = request.args.get('tab', 'all')
        search_query = request.args.get('query', '').strip()

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

        if tab_type == 'processing':
            query = query.filter(Product.image_status == 'PROCESSING')
        elif tab_type == 'ready':
            query = query.filter(or_(
                Product.image_status == 'READY',
                Product.image_status == None
            ))
        elif tab_type == 'failed':
            query = query.filter(Product.image_status == 'FAILED')
        elif tab_type == 'completed':
            query = query.filter(Product.image_status == 'COMPLETED')
        
        if search_query:
            search_term = f"%{search_query.upper()}%"
            query = query.filter(or_(
                Product.product_number.ilike(search_term),
                Product.product_name.ilike(search_term)
            ))

        pagination = query.order_by(
            case(
                (Product.image_status == 'PROCESSING', 1),
                (Product.image_status == 'FAILED', 2),
                else_=3
            ),
            Product.product_number.asc()
        ).paginate(page=page, per_page=limit, error_out=False)

        result_list = []
        for row in pagination.items:
            item = {
                'style_code': row.product_number,
                'product_name': row.product_name,
                'status': row.image_status or 'READY',
                'thumbnail': row.thumbnail_url,
                'detail': row.detail_image_url,
                'drive_link': row.image_drive_link,
                'message': row.last_message,
                'total_colors': row.total_colors
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
    options = data.get('options', {})
    
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
                style_codes,
                options
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

@api_bp.route('/api/product/download/<style_code>', methods=['GET'])
@login_required
def download_product_images(style_code):
    if not current_user.brand_id:
        return jsonify({'status': 'error', 'message': '권한 없음'}), 403

    try:
        brand_name = current_user.brand.brand_name
        base_path = os.path.join(current_app.root_path, 'static', 'product_images', brand_name, style_code)
        
        if not os.path.exists(base_path):
            return jsonify({'status': 'error', 'message': '이미지 폴더를 찾을 수 없습니다.'}), 404
            
        zip_filename = f"{style_code}_images.zip"
        zip_io = io.BytesIO()
        
        with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, base_path)
                    zipf.write(file_path, arcname)
        
        zip_io.seek(0)
        
        return send_file(
            zip_io,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/product/delete_image_data', methods=['POST'])
@login_required
def delete_product_image_data():
    if not current_user.brand_id:
        return jsonify({'status': 'error', 'message': '권한 없음'}), 403
        
    data = request.json
    style_codes = data.get('style_codes', [])
    
    if not style_codes:
        return jsonify({'status': 'error', 'message': '선택된 항목이 없습니다.'}), 400
        
    try:
        count = 0
        brand_name = current_user.brand.brand_name
        
        for code in style_codes:
            products = Product.query.filter(
                Product.brand_id == current_user.current_brand_id,
                Product.product_number.like(f"{code}%")
            ).all()
            
            for p in products:
                p.image_status = 'READY'
                p.thumbnail_url = None
                p.detail_image_url = None
                p.image_drive_link = None
                p.last_message = None
                
            folder_path = os.path.join(current_app.root_path, 'static', 'product_images', brand_name, code)
            if os.path.exists(folder_path):
                try:
                    shutil.rmtree(folder_path)
                except Exception as fs_err:
                    print(f"File delete error: {fs_err}")
            
            count += 1
            
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'{count}건의 이미지 데이터 및 파일을 삭제했습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500