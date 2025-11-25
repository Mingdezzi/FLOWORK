from flask import render_template, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from flowork.models import db, StockTransfer, Store
from . import ui_bp

@ui_bp.route('/stock_transfer/out')
@login_required
def stock_transfer_out():
    """수평출고 현황 (내가 보내야 할 목록)"""
    if not current_user.store_id:
        abort(403, description="매장 계정 전용 기능입니다.")
        
    # 내가 보내야 하는 것들 (상태: REQUESTED, SHIPPED, REJECTED 등)
    transfers = StockTransfer.query.filter_by(
        source_store_id=current_user.store_id
    ).order_by(StockTransfer.created_at.desc()).all()
    
    return render_template('stock_transfer_out.html', active_page='transfer_out', transfers=transfers)

@ui_bp.route('/stock_transfer/in')
@login_required
def stock_transfer_in():
    """수평입고 현황 (내가 받아야 할 목록 및 요청 등록)"""
    if not current_user.store_id:
        abort(403, description="매장 계정 전용 기능입니다.")
        
    # 내가 받아야 하는 것들
    transfers = StockTransfer.query.filter_by(
        target_store_id=current_user.store_id
    ).order_by(StockTransfer.created_at.desc()).all()
    
    # 요청 가능한 다른 매장 목록
    other_stores = Store.query.filter(
        Store.brand_id == current_user.current_brand_id,
        Store.id != current_user.store_id,
        Store.is_active == True
    ).all()
    
    return render_template('stock_transfer_in.html', active_page='transfer_in', transfers=transfers, stores=other_stores)

@ui_bp.route('/stock_transfer/status')
@login_required
def stock_transfer_status():
    """수평이동 전체 현황 (본사 관리자용 / 매장 조회용)"""
    query = StockTransfer.query.join(StockTransfer.source_store).filter(
        Store.brand_id == current_user.current_brand_id
    )
    
    if current_user.store_id:
        # 매장은 본인이 관여된 것만
        query = query.filter(
            or_(StockTransfer.source_store_id == current_user.store_id,
                StockTransfer.target_store_id == current_user.store_id)
        )
        
    transfers = query.order_by(StockTransfer.created_at.desc()).limit(100).all()
    return render_template('stock_transfer_status.html', active_page='transfer_status', transfers=transfers)