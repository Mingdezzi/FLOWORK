import uuid
import threading
import traceback
import os
import io
import shutil
import zipfile
import json
from flask import request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from sqlalchemy import text, func, or_, case
from flowork.models import db, Product, Variant, Setting
from . import api_bp
from flowork.celery_tasks import task_process_images

@api_bp.route('/api/product/images', methods=['GET'])
@login_required
def get_product_image_status():
    if not current_user.brand_id:
        return jsonify({'status': 'error', 'message': '브랜드 계정이 필요합니다.'}), 403

    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        tab_type = request.args.get('tab', 'all')
        
        # [수정] 다중 품번 및 상세 검색 파라미터 처리
        multi_codes_str = request.args.get('multi_codes', '')
        batch_codes_str = request.args.get('batch_codes', '')
        
        search_name = request.args.get('product_name', '').strip()
        search_year = request.args.get('release_year', '').strip()
        search_category = request.args.get('item_category', '').strip()

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

        # 1. 현재 작업 배치 필터링 (상단 탭용)
        if batch_codes_str:
            batch_codes = [c.strip() for c in batch_codes_str.split(',') if c.strip()]
            if batch_codes:
                # 배치 코드로 시작하는 것 검색 (LIKE prefix)
                conditions = [Product.product_number.like(f"{code}%") for code in batch_codes]
                query = query.filter(or_(*conditions))

        # 2. 상세 검색 필터링 (하단 탭용)
        if multi_codes_str:
            # 줄바꿈으로 분리된 다중 품번
            codes = [c.strip() for c in multi_codes_str.split('\n') if c.strip()]
            if codes:
                # 입력된 코드로 시작하는 품번 검색
                conditions = [Product.product_number.like(f"{code}%") for code in codes]
                query = query.filter(or_(*conditions))
        
        if search_name:
            query = query.filter(Product.product_name_cleaned.like(f"%{search_name}%"))
        if search_year:
            try:
                query = query.filter(Product.release_year == int(search_year))
            except: pass
        if search_category:
            query = query.filter(Product.item_category == search_category)

        # 3. 탭 상태 필터링
        if tab_type == 'processing':
            query = query.filter(Product.image_status == 'PROCESSING')
        elif tab_type == 'ready':
            query = query.filter(or_(Product.image_status == 'READY', Product.image_status == None))
        elif tab_type == 'failed':
            query = query.filter(Product.image_status == 'FAILED')
        elif tab_type == 'completed':
            query = query.filter(Product.image_status == 'COMPLETED')

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
        save_options_logic(current_user.id, current_user.current_brand_id, options)

        for code in style_codes:
            db.session.query(Product).filter(
                Product.brand_id == current_user.current_brand_id,
                Product.product_number.like(f"{code}%")
            ).update({
                Product.image_status: 'PROCESSING',
                Product.last_message: '작업 시작됨...'
            }, synchronize_session=False)
            
        db.session.commit()

        task = task_process_images.delay(
            current_user.current_brand_id,
            style_codes,
            options
        )

        return jsonify({
            'status': 'success', 
            'message': '이미지 처리가 시작되었습니다.', 
            'task_id': task.id
        })

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

def save_options_logic(user_id, brand_id, options):
    key = f'USER_OPTS_{user_id}'
    value_str = json.dumps(options, ensure_ascii=False)
    
    setting = Setting.query.filter_by(brand_id=brand_id, key=key).first()
    if setting:
        setting.value = value_str
    else:
        setting = Setting(brand_id=brand_id, key=key, value=value_str)
        db.session.add(setting)
    db.session.commit()

@api_bp.route('/api/product/options', methods=['GET'])
@login_required
def get_user_options():
    if not current_user.brand_id: return jsonify({'status': 'error'}), 403
    
    key = f'USER_OPTS_{current_user.id}'
    setting = Setting.query.filter_by(brand_id=current_user.current_brand_id, key=key).first()
    
    options = {}
    if setting and setting.value:
        try:
            options = json.loads(setting.value)
        except:
            pass
            
    return jsonify({'status': 'success', 'options': options})

@api_bp.route('/api/product/folder/<style_code>', methods=['GET'])
@login_required
def get_product_folder_images(style_code):
    if not current_user.brand_id: return jsonify({'status': 'error'}), 403
    
    try:
        brand_name = current_user.brand.brand_name
        base_path = os.path.join(current_app.root_path, 'static', 'product_images', brand_name, style_code)
        
        if not os.path.exists(base_path):
            return jsonify({'status': 'error', 'message': '폴더를 찾을 수 없습니다.'}), 404
            
        images = []
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, current_app.root_path)
                    web_path = '/' + rel_path.replace('\\', '/')
                    images.append({
                        'name': file,
                        'path': web_path,
                        'type': 'processed' if '_nobg' in file else 'original'
                    })
                    
        return jsonify({'status': 'success', 'images': images})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/product/images/reset', methods=['POST'])
@login_required
def reset_image_process_status():
    if not current_user.brand_id: return jsonify({'status': 'error'}), 403
    data = request.json
    style_codes = data.get('style_codes', [])
    if not style_codes: return jsonify({'status': 'error'}), 400
    try:
        count = 0
        for code in style_codes:
            res = db.session.query(Product).filter(
                Product.brand_id == current_user.current_brand_id,
                Product.product_number.like(f"{code}%")
            ).update({Product.image_status: 'READY', Product.last_message: '초기화됨'}, synchronize_session=False)
            count += res
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'{count}건 초기화'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/product/images/reset_all_processing', methods=['POST'])
@login_required
def reset_all_processing_status():
    if not current_user.brand_id: return jsonify({'status': 'error'}), 403
    try:
        res = db.session.query(Product).filter(
            Product.brand_id == current_user.current_brand_id,
            Product.image_status == 'PROCESSING'
        ).update({Product.image_status: 'READY', Product.last_message: '일괄 초기화'}, synchronize_session=False)
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'{res}건 초기화'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/product/download/<style_code>', methods=['GET'])
@login_required
def download_product_images(style_code):
    if not current_user.brand_id: return jsonify({'status': 'error'}), 403
    try:
        brand_name = current_user.brand.brand_name
        base_path = os.path.join(current_app.root_path, 'static', 'product_images', brand_name, style_code)
        if not os.path.exists(base_path): return jsonify({'status': 'error', 'message': '폴더 없음'}), 404
        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, base_path)
                    zipf.write(file_path, arcname)
        zip_io.seek(0)
        return send_file(zip_io, mimetype='application/zip', as_attachment=True, download_name=f"{style_code}_images.zip")
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/product/delete_image_data', methods=['POST'])
@login_required
def delete_product_image_data():
    if not current_user.brand_id: return jsonify({'status': 'error'}), 403
    data = request.json
    style_codes = data.get('style_codes', [])
    if not style_codes: return jsonify({'status': 'error'}), 400
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
                try: shutil.rmtree(folder_path)
                except: pass
            count += 1
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'{count}건 삭제 완료'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500