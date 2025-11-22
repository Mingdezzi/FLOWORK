from flask import render_template, abort
from flask_login import login_required, current_user
from flowork.modules.operations import operations_bp

@operations_bp.route('/attendance')
@login_required
def attendance_page():
    if not current_user.store_id: abort(403)
    return render_template('attendance.html', active_page='attendance')

@operations_bp.route('/competitor_sales')
@login_required
def competitor_sales_page():
    if not current_user.store_id: abort(403)
    return render_template('competitor_sales.html', active_page='competitor_sales')