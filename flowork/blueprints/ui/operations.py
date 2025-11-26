from flask import render_template, request, abort
from flask_login import login_required, current_user
from flowork.models import Staff
from . import ui_bp

@ui_bp.route('/attendance')
@login_required
def attendance_page():
    if not current_user.store_id:
        abort(403, description="매장 계정 전용입니다.")
    return render_template('attendance.html', active_page='attendance')

@ui_bp.route('/competitor_sales')
@login_required
def competitor_sales_page():
    if not current_user.store_id:
        abort(403, description="매장 계정 전용입니다.")
    return render_template('competitor_sales.html', active_page='competitor_sales')