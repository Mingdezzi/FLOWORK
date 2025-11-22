import traceback
import os
from flask import current_app
from flowork.extensions import celery
from flowork.services.excel import process_stock_upsert_excel, import_excel_file
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

@celery.task(bind=True)
def task_upsert_inventory(self, file_path, form_data, upload_mode, brand_id, target_store_id, excluded_indices, allow_create):
    try:
        def progress_callback(current, total):
            self.update_state(state='PROGRESS', meta={'current': current, 'total': total, 'percent': int((current / total) * 100) if total > 0 else 0})

        processed, created, message, category = process_stock_upsert_excel(
            file_path, form_data, upload_mode, 
            brand_id, 
            target_store_id,
            progress_callback=progress_callback,
            excluded_row_indices=excluded_indices,
            allow_create=allow_create
        )
        
        return {
            'status': 'completed',
            'result': {'message': message, 'category': category}
        }
    except Exception as e:
        traceback.print_exc()
        return {'status': 'error', 'message': str(e)}
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@celery.task(bind=True)
def task_import_db(self, file_path, form_data, brand_id):
    try:
        def progress_callback(current, total):
            self.update_state(state='PROGRESS', meta={'current': current, 'total': total, 'percent': int((current / total) * 100) if total > 0 else 0})

        with open(file_path, 'rb') as f:
            success, message, category = import_excel_file(
                f, form_data, brand_id,
                progress_callback=progress_callback
            )
        
        if success:
            return {
                'status': 'completed',
                'result': {'message': message, 'category': category}
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