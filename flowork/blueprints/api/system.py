from flask import jsonify, request
from flask_login import login_required, current_user
from flowork.blueprints.api.utils import admin_required
from flowork.services.version_service import VersionService
from flowork.models import UpdateLog
from . import api_bp

@api_bp.route('/api/system/logs', methods=['GET'])
@login_required
def get_update_logs():
    logs = UpdateLog.query.order_by(UpdateLog.created_at.desc()).all()
    data = [{
        'version': log.version,
        'title': log.title,
        'content': log.content,
        'date': log.created_at.strftime('%Y-%m-%d %H:%M'),
        'admin': log.created_by.username if log.created_by else 'System'
    } for log in logs]
    return jsonify({'status': 'success', 'logs': data})

@api_bp.route('/api/system/logs/auto', methods=['POST'])
@admin_required
def create_auto_log():
    result = VersionService.generate_auto_log(current_user.id)
    return jsonify(result)