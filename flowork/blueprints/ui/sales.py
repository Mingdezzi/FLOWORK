from flask import render_template, request, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import date, datetime

from flowork.models import db, Sale, SaleItem
from . import ui_bp

@ui_bp.route('/sales')
@login_required
def sales_register():
    if not current_user.store_id:
        abort(403, description="판매 등록은 매장 계정만 사용할 수 있습니다.")
    return render_template('sales.html', active_page='sales')

@ui_bp.route('/sales/record')
@login_required
def sales_record():
    if not current_user.store_id:
        abort(403, description="판매 내역은 매장 계정만 사용할 수 있습니다.")
        
    # 1. 기간 파라미터 받기 (기본값: 오늘)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    today = date.today()
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else today
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else today
    
    page = request.args.get('page', 1, type=int)
    
    # 2. 기본 쿼리 (매장 + 기간)
    query = Sale.query.filter(
        Sale.store_id == current_user.store_id,
        Sale.sale_date >= start_date,
        Sale.sale_date <= end_date
    )
    
    # 3. 리스트 조회 (최신순 페이징)
    pagination = query.order_by(Sale.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    # 4. 통계 집계 (유효한 매출 기준: status='valid')
    # (환불된 건은 매출 통계에서 제외)
    
    # 4-1. 총 판매 금액 & 건수
    stats_query = db.session.query(
        func.sum(Sale.total_amount),
        func.count(Sale.id)
    ).filter(
        Sale.store_id == current_user.store_id,
        Sale.sale_date >= start_date,
        Sale.sale_date <= end_date,
        Sale.status == 'valid'
    )
    total_amount, total_count = stats_query.first()
    
    # 4-2. 총 할인 금액 (SaleItem join 필요, 수량 고려)
    total_discount = db.session.query(
        func.sum(SaleItem.discount_amount * SaleItem.quantity)
    ).join(Sale).filter(
        Sale.store_id == current_user.store_id,
        Sale.sale_date >= start_date,
        Sale.sale_date <= end_date,
        Sale.status == 'valid'
    ).scalar()
    
    total_summary = {
        'total_amount': int(total_amount or 0),
        'total_discount': int(total_discount or 0),
        'total_count': int(total_count or 0)
    }
    
    return render_template(
        'sales_record.html', 
        active_page='sales_record', # 네비게이션 활성화 수정 (기존 'sales' -> 'sales_record')
        pagination=pagination, 
        sales=pagination.items,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        total_summary=total_summary
    )

@ui_bp.route('/sales/<int:sale_id>')
@login_required
def sales_detail(sale_id):
    if not current_user.store_id:
        abort(403, description="매장 계정만 접근 가능합니다.")
        
    sale = Sale.query.filter_by(id=sale_id, store_id=current_user.store_id).first()
    if not sale:
        abort(404, description="판매 내역을 찾을 수 없습니다.")
        
    # 상세 페이지에서도 '판매현황' 탭 활성화 유지
    return render_template('sales_detail.html', active_page='sales_record', sale=sale)