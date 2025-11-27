from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from . import ui_bp

@ui_bp.route('/')
@login_required
def home():
    """
    [최적화] 대시보드 페이지 (껍데기만 렌더링)
    실제 데이터는 클라이언트(index.js)에서 /api/dashboard/stats 호출로 비동기 로드합니다.
    """
    if current_user.is_super_admin:
        flash("슈퍼 관리자 계정입니다. (시스템 설정)", "info")
        return redirect(url_for('ui.setting_page'))
    
    # active_page='home'을 전달하여 index.js의 DashboardApp이 실행되도록 함
    return render_template('index.html', active_page='home')