import os
import traceback
from flowork.extensions import celery
# [중요] 여기서 import 하는 함수들은 이미 제공된 excel_services.py, image_services.py에 있어야 합니다.
from flowork.modules.product.excel_services import process_stock_upsert, import_db_full
from flowork.modules.product.image_services import process_style_code_group

@celery.task(bind=True)
def task_process_images(self, brand_id, style_codes, options):
    total = len(style_codes)
    success_count = 0
    results = []
    try:
        for i, code in enumerate(style_codes):
            self.update_state(state='PROGRESS', meta={'current': i, 'total': total, 'percent': int((i/total)*100)})
            success, msg = process_style_code_group(brand_id, code, options)
            results.append({'code': code, 'success': success, 'message': msg})
            if success: success_count += 1
            
        return {
            'status': 'completed',
            'current': total, 'total': total, 'percent': 100,
            'result': {'message': f"처리 완료: 성공 {success_count}/{total}건", 'details': results}
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@celery.task(bind=True)
def task_upsert_inventory(self, file_path, form_data, mode, brand_id, store_id, excluded, allow_create):
    try:
        def cb(curr, tot):
            # 진행률 업데이트 콜백
            if tot > 0:
                self.update_state(state='PROGRESS', meta={'current': curr, 'total': tot, 'percent': int((curr/tot)*100)})
            
        upd, crt, msg, _ = process_stock_upsert(file_path, form_data, mode, brand_id, store_id, cb, allow_create)
        return {'status': 'completed', 'result': {'message': msg}}
    except Exception as e:
        traceback.print_exc()
        return {'status': 'error', 'message': str(e)}
    finally:
        # 작업 완료 후 임시 파일 삭제
        if os.path.exists(file_path): os.remove(file_path)

@celery.task(bind=True)
def task_import_db(self, file_path, form_data, brand_id):
    try:
        def cb(curr, tot):
            if tot > 0:
                self.update_state(state='PROGRESS', meta={'current': curr, 'total': tot, 'percent': int((curr/tot)*100)})
            
        success, msg, _ = import_db_full(file_path, form_data, brand_id, cb)
        if success: return {'status': 'completed', 'result': {'message': msg}}
        return {'status': 'error', 'message': msg}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    finally:
        if os.path.exists(file_path): os.remove(file_path)