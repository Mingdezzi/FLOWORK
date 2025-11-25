import traceback
import os
import gc
from flask import current_app
from flowork.extensions import celery
from flowork.services.excel import parse_stock_excel, verify_stock_excel
from flowork.services.inventory_service import InventoryService
from flowork.services.image_process import process_style_code_group

@celery.task(bind=True)
def task_process_images(self, brand_id, style_codes, options):
    total = len(style_codes)
    success_count = 0
    results = []

    try:
        for i, code in enumerate(style_codes):
            self.update_state(state='PROGRESS', meta={'current': i, 'total': total, 'percent': int((i / total) * 100)})
            
            success, msg = process_style_code_group(brand_id, code, options=options)
            results.append({'code': code, 'success': success, 'message': msg})
            if success:
                success_count += 1
        
        return {
            'status': 'completed',
            'current': total,
            'total': total,
            'percent': 100,
            'result': {
                'message': f"이미지 처리 완료: 성공 {success_count}/{total}건",
                'details': results
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
    finally:
        # [신규] 이미지 처리 후 메모리 강제 회수 (누수 방지)
        gc.collect()

@celery.task(bind=True)
def task_upsert_inventory(self, file_path, form_data, upload_mode, brand_id, target_store_id, excluded_indices, allow_create):
    try:
        # 1. 엑셀 파싱 (Pure Logic)
        records, error_msg = parse_stock_excel(
            file_path, form_data, upload_mode, brand_id, excluded_indices
        )
        
        if error_msg or not records:
            return {'status': 'error', 'message': error_msg or "데이터 파싱 실패"}

        # 2. DB 업데이트 (Service Logic)
        def progress_callback(current, total):
            self.update_state(state='PROGRESS', meta={'current': current, 'total': total, 'percent': int((current / total) * 100) if total > 0 else 0})

        cnt_update, cnt_var, message = InventoryService.process_stock_data(
            records, upload_mode, brand_id, target_store_id, allow_create, progress_callback
        )
        
        return {
            'status': 'completed',
            'result': {'message': message}
        }
    except Exception as e:
        traceback.print_exc()
        return {'status': 'error', 'message': str(e)}
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        # [신규] 대용량 엑셀 처리 후에도 메모리 정리
        gc.collect()

@celery.task(bind=True)
def task_import_db(self, file_path, form_data, brand_id):
    try:
        # 1. 엑셀 파싱
        records, error_msg = parse_stock_excel(
            file_path, form_data, 'db', brand_id, None
        )
        
        if error_msg or not records:
            return {'status': 'error', 'message': error_msg or "데이터 파싱 실패"}

        # 2. DB 전체 초기화 및 삽입
        def progress_callback(current, total):
            self.update_state(state='PROGRESS', meta={'current': current, 'total': total, 'percent': int((current / total) * 100) if total > 0 else 0})

        success, message = InventoryService.full_import_db(
            records, brand_id, progress_callback
        )
        
        if success:
            return {
                'status': 'completed',
                'result': {'message': message}
            }
        else:
            return {
                'status': 'error',
                'message': message
            }
    except Exception as e:
        traceback.print_exc()
        return {'status': 'error', 'message': str(e)}
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        # [신규] 메모리 정리
        gc.collect()
