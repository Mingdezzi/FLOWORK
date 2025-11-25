from flask import render_template, abort
from flask_login import login_required, current_user
from . import ui_bp
from flowork.services.db import get_filter_options_from_db

@ui_bp.route('/online/management')
@login_required
def online_management():
    if not current_user.brand_id:
        abort(403, description="접근 권한이 없습니다. (브랜드 소속 계정 전용)")

    filter_options = get_filter_options_from_db(current_user.current_brand_id)

    return render_template('online_mgmt.html', 
                           active_page='online_mgmt',
                           filter_options=filter_options)