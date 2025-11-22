from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy.orm import selectinload
from flowork.modules.main import main_bp
from flowork.models import Announcement, Order, ScheduleEvent
from flowork.constants import OrderStatus

@main_bp.route('/')
@login_required
def home():
    if current_user.is_super_admin:
        flash("슈퍼 관리자 접속", "info")
        return redirect(url_for('admin.setting_page'))
        
    bid = current_user.current_brand_id
    sid = current_user.store_id
    
    notices = Announcement.query.filter_by(brand_id=bid).order_by(Announcement.created_at.desc()).limit(5).all()
    orders = []
    schedules = []
    
    if sid:
        orders = Order.query.filter(Order.store_id==sid, Order.order_status.in_(OrderStatus.PENDING)).order_by(Order.created_at.desc()).limit(5).all()
        today = datetime.now().date()
        schedules = ScheduleEvent.query.options(selectinload(ScheduleEvent.staff)).filter(ScheduleEvent.store_id==sid, ScheduleEvent.start_time>=today, ScheduleEvent.start_time<today+timedelta(days=7)).order_by(ScheduleEvent.start_time).all()
        
    return render_template('index.html', active_page='home', recent_announcements=notices, pending_orders=orders, weekly_schedules=schedules)