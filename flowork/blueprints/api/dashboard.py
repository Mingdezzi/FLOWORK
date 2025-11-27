from flask import jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from flowork.models import db, Announcement, Order, ScheduleEvent
from flowork.constants import OrderStatus
from . import api_bp

@api_bp.route('/api/dashboard/stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    """
    대시보드용 통합 데이터 조회 API
    공지사항, 진행 중인 주문, 주간 일정을 JSON으로 반환합니다.
    """
    try:
        current_brand_id = current_user.current_brand_id
        store_id = current_user.store_id
        
        # 1. 최근 공지사항 (최신순 5개)
        announcements = Announcement.query.filter_by(
            brand_id=current_brand_id
        ).order_by(Announcement.created_at.desc()).limit(5).all()
        
        announcement_data = [{
            'id': a.id,
            'title': a.title,
            'content_preview': a.content[:50] + '...' if a.content else '',
            'date': a.created_at.strftime('%Y-%m-%d')
        } for a in announcements]
        
        # 2. 진행 중인 주문 (매장 계정 전용, 최신순 5개)
        pending_orders_data = []
        if store_id:
            pending_orders = Order.query.filter(
                Order.store_id == store_id,
                Order.order_status.in_(OrderStatus.PENDING)
            ).order_by(Order.created_at.desc()).limit(5).all()
            
            pending_orders_data = [{
                'id': o.id,
                'customer_name': o.customer_name,
                'product_name': o.product_name,
                'status': o.order_status,
                'date': o.created_at.strftime('%m-%d')
            } for o in pending_orders]
            
        # 3. 주간 일정 (매장 계정 전용, 오늘부터 7일간)
        weekly_schedules_data = []
        if store_id:
            today = datetime.now().date()
            next_week = today + timedelta(days=7)
            
            schedules = ScheduleEvent.query.options(
                selectinload(ScheduleEvent.staff)
            ).filter(
                ScheduleEvent.store_id == store_id,
                ScheduleEvent.start_time >= today,
                ScheduleEvent.start_time < next_week
            ).order_by(ScheduleEvent.start_time).all()
            
            for s in schedules:
                start_dt = s.start_time.strftime('%m-%d')
                # 종료일이 있고 시작일과 다르면 기간으로 표시
                end_dt = s.end_time.strftime('%m-%d') if s.end_time else None
                date_str = f"{start_dt}"
                if end_dt and end_dt != start_dt:
                    date_str += f" ~ {end_dt}"
                    
                weekly_schedules_data.append({
                    'color': s.color,
                    'type': s.event_type,
                    'title': s.title,
                    'staff_name': s.staff.name if s.staff else '전체',
                    'date_str': date_str
                })

        return jsonify({
            'status': 'success',
            'data': {
                'announcements': announcement_data,
                'pending_orders': pending_orders_data,
                'weekly_schedules': weekly_schedules_data,
                'is_store': bool(store_id)
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500