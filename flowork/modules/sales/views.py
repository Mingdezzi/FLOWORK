from datetime import date, datetime
from flask import render_template, request, abort
from flask_login import login_required, current_user
from flowork.modules.sales import sales_bp
from flowork.modules.sales.services import get_sales_list, get_sales_stats
from flowork.models import Sale

@sales_bp.route('/sales')
@login_required
def sales_register_view():
    if not current_user.store_id: abort(403)
    return render_template('sales.html', active_page='sales')

@sales_bp.route('/sales/record')
@login_required
def sales_record_view():
    if not current_user.store_id: abort(403)
    s_str = request.args.get('start_date')
    e_str = request.args.get('end_date')
    
    today = date.today()
    start = datetime.strptime(s_str, '%Y-%m-%d').date() if s_str else today
    end = datetime.strptime(e_str, '%Y-%m-%d').date() if e_str else today
    
    pg = request.args.get('page', 1, type=int)
    pagination = get_sales_list(current_user.store_id, start, end, pg)
    stats = get_sales_stats(current_user.store_id, start, end)
    
    return render_template('sales_record.html', active_page='sales_record', 
                           pagination=pagination, sales=pagination.items,
                           start_date=start.strftime('%Y-%m-%d'), end_date=end.strftime('%Y-%m-%d'),
                           total_summary=stats)

@sales_bp.route('/sales/<int:sale_id>')
@login_required
def sales_detail_view(sale_id):
    if not current_user.store_id: abort(403)
    sale = Sale.query.filter_by(id=sale_id, store_id=current_user.store_id).first()
    if not sale: abort(404)
    return render_template('sales_detail.html', active_page='sales_record', sale=sale)