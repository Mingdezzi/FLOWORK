from flask import jsonify
from flowork.celery_tasks import task_process_images

from . import api_bp

@api_bp.route('/api/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = task_process_images.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'status': 'processing',
            'current': 0,
            'total': 0,
            'percent': 0
        }
    elif task.state == 'PROGRESS':
        response = {
            'status': 'processing',
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 0),
            'percent': task.info.get('percent', 0)
        }
    elif task.state == 'SUCCESS':
        result = task.result
        # task.result가 딕셔너리 형태인지 확인
        if isinstance(result, dict):
            response = result
        else:
             response = {
                'status': 'completed',
                'result': result
            }
    else:
        response = {
            'status': 'error',
            'message': str(task.info)
        }
        
    return jsonify(response)