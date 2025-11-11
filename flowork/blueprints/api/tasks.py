import os
import uuid
import traceback
from flask import jsonify, current_app
from . import api_bp
# [수정] services 패키지 경로 수정
from flowork.services.excel import process_stock_upsert_excel

TASKS = {}

def update_task_status(task_id, current, total):
    if task_id in TASKS:
        TASKS[task_id]['current'] = current
        TASKS[task_id]['total'] = total
        TASKS[task_id]['percent'] = int((current / total) * 100) if total > 0 else 0

def run_async_stock_upsert(app, task_id, file_path, form, stock_type, brand_id, target_store_id, excluded_indices):
    """백그라운드 스레드에서 실행될 함수"""
    with app.app_context():
        try:
            processed, created, message, category = process_stock_upsert_excel(
                file_path, form, stock_type, 
                brand_id, 
                target_store_id,
                progress_callback=lambda c, t: update_task_status(task_id, c, t),
                excluded_row_indices=excluded_indices
            )
            TASKS[task_id]['status'] = 'completed'
            TASKS[task_id]['result'] = {'message': message, 'category': category}
        except Exception as e:
            print(f"Async task error: {e}")
            traceback.print_exc()
            TASKS[task_id]['status'] = 'error'
            TASKS[task_id]['message'] = str(e)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

@api_bp.route('/api/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = TASKS.get(task_id)
    if not task:
        return jsonify({'status': 'not_found'}), 404
    
    if task['status'] in ['completed', 'error']:
        response = jsonify(task)
        del TASKS[task_id]
        return response
        
    return jsonify(task)