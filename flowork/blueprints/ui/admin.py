import json
import os
import traceback
from flask import render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user

from flowork.models import db, Announcement, Setting, Brand, Store, Staff, Comment
from . import ui_bp

@ui_bp.route('/setting')
@login_required
def setting_page():
    if not current_user.is_admin and not current_user.is_super_admin:
        abort(403, description="설정 페이지는 관리자만 접근할 수 있습니다.")

    try:
        current_brand_id = current_user.current_brand_id
        my_store_id = current_user.store_id
        
        brand_name_display = "FLOWORK (Super Admin)"
        all_stores_in_brand = []
        staff_list = []
        hq_store_id_setting = None
        category_config = None
        
        expected_filename = None
        loaded_settings_file = None

        if current_brand_id:
            brand_name_setting = Setting.query.filter_by(brand_id=current_brand_id, key='BRAND_NAME').first()
            brand = db.session.get(Brand, current_brand_id)
            brand_name_display = (brand_name_setting.value if brand_name_setting else brand.brand_name) or "브랜드 이름 없음"

            all_stores_in_brand = Store.query.filter(Store.brand_id == current_brand_id).order_by(Store.store_name).all()
            
            if not my_store_id: 
                hq_setting = Setting.query.filter_by(brand_id=current_brand_id, key='HQ_STORE_ID').first()
                if hq_setting and hq_setting.value:
                    hq_store_id_setting = int(hq_setting.value)
                
                category_setting = Setting.query.filter_by(brand_id=current_brand_id, key='CATEGORY_CONFIG').first()
                if category_setting and category_setting.value:
                    try:
                        category_config = json.loads(category_setting.value)
                    except json.JSONDecodeError:
                        pass
                
                if brand:
                    expected_filename = f"{brand.brand_name}.json"
                loaded_setting = Setting.query.filter_by(
                    brand_id=current_brand_id, 
                    key='LOADED_SETTINGS_FILE'
                ).first()
                if loaded_setting:
                    loaded_settings_file = loaded_setting.value
        
        if my_store_id:
            staff_list = Staff.query.filter(Staff.store_id == my_store_id, Staff.is_active == True).order_by(Staff.name).all()
        
        context = {
            'active_page': 'setting',
            'brand_name': brand_name_display,
            'my_store_id': my_store_id, 
            'all_stores': all_stores_in_brand, 
            'staff_list': staff_list,
            'hq_store_id_setting': hq_store_id_setting,
            'category_config': category_config,
            'expected_settings_file': expected_filename,
            'loaded_settings_file': loaded_settings_file
        }
        return render_template('setting.html', **context)
    
    except Exception as e:
        print(f"Error loading setting page: {e}")
        traceback.print_exc()
        abort(500, description="설정 페이지를 불러오는 중 오류가 발생했습니다.")

@ui_bp.route('/schedule')
@login_required
def schedule():
    if not current_user.store_id:
        abort(403, description="매장 일정은 매장 계정만 사용할 수 있습니다.")

    staff_list = Staff.query.filter(
        Staff.store_id == current_user.store_id,
        Staff.is_active == True
    ).order_by(Staff.name).all()
    
    return render_template('schedule.html', active_page='schedule', staff_list=staff_list) 

@ui_bp.route('/announcements')
@login_required
def announcement_list():
    if current_user.is_super_admin:
        abort(403, description="슈퍼 관리자는 공지사항을 볼 수 없습니다.")
    try:
        items = Announcement.query.filter(
            Announcement.brand_id == current_user.current_brand_id
        ).order_by(Announcement.created_at.desc()).all()
        return render_template('announcements.html', active_page='announcements', announcements=items)
    except Exception as e:
        print(f"Error loading announcements: {e}")
        traceback.print_exc()
        abort(500, description="공지사항 로드 중 오류가 발생했습니다.")

@ui_bp.route('/announcement/<id>', methods=['GET', 'POST'])
@login_required
def announcement_detail(id):
    if current_user.is_super_admin:
        abort(403, description="슈퍼 관리자는 공지사항을 관리할 수 없습니다.")

    item = None
    current_brand_id = current_user.current_brand_id
    
    is_hq_admin = (current_user.brand_id is not None) and (current_user.store_id is None)

    if id == 'new':
        if not is_hq_admin:
            abort(403, description="공지사항 작성 권한이 없습니다. (본사 관리자 전용)")
        item = Announcement(title='', content='')
    else:
        item = Announcement.query.filter_by(id=int(id), brand_id=current_brand_id).first()
        if not item: abort(404, description="공지사항을 찾을 수 없거나 권한이 없습니다.")

    if request.method == 'POST':
        if not is_hq_admin:
            abort(403, description="공지사항 수정 권한이 없습니다. (본사 관리자 전용)")
            
        try:
            item.title = request.form['title']
            item.content = request.form['content']
            if id == 'new':
                item.brand_id = current_brand_id
                db.session.add(item)
                flash("새 공지사항이 등록되었습니다.", "success")
            else:
                flash("공지사항이 수정되었습니다.", "success")
            db.session.commit()
            return redirect(url_for('ui.announcement_detail', id=item.id))
        except Exception as e:
            db.session.rollback()
            print(f"Error saving announcement: {e}")
            traceback.print_exc()
            flash(f"저장 중 오류 발생: {e}", "error")

    comments = []
    if item and item.id:
        comments = item.comments.order_by(Comment.created_at.asc()).all()

    return render_template('announcement_detail.html', 
                           active_page='announcements', 
                           item=item, 
                           is_hq_admin=is_hq_admin,
                           comments=comments)

@ui_bp.route('/announcement/delete/<int:id>', methods=['POST'])
@login_required
def delete_announcement(id):
    if current_user.store_id or not current_user.brand_id:
        abort(403, description="공지사항 삭제 권한이 없습니다. (본사 관리자 전용)")
        
    if current_user.is_super_admin:
        abort(403, description="슈퍼 관리자는 공지사항을 관리할 수 없습니다.")
        
    try:
        item = Announcement.query.filter_by(id=int(id), brand_id=current_user.current_brand_id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            flash(f"공지사항(제목: {item.title})이(가) 삭제되었습니다.", "success")
        else:
            flash("삭제할 공지사항을 찾을 수 없거나 권한이 없습니다.", "warning")
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting announcement {id}: {e}")
        flash(f"공지사항 삭제 중 오류 발생: {e}", "error")
    return redirect(url_for('ui.announcement_list'))

@ui_bp.route('/announcement/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    content = request.form.get('content', '').strip()
    if not content:
        flash("댓글 내용을 입력해주세요.", "warning")
        return redirect(url_for('ui.announcement_detail', id=id))
        
    try:
        announcement = Announcement.query.filter_by(id=id, brand_id=current_user.current_brand_id).first()
        if not announcement:
            abort(404, description="공지사항을 찾을 수 없습니다.")
            
        comment = Comment(
            announcement_id=id,
            user_id=current_user.id,
            content=content
        )
        db.session.add(comment)
        db.session.commit()
        flash("댓글이 등록되었습니다.", "success")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding comment: {e}")
        flash(f"댓글 등록 중 오류 발생: {e}", "error")
        
    return redirect(url_for('ui.announcement_detail', id=id))

@ui_bp.route('/comment/delete/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    try:
        comment = db.session.get(Comment, comment_id)
        if not comment:
            abort(404, description="댓글을 찾을 수 없습니다.")
            
        is_author = (comment.user_id == current_user.id)
        is_hq_admin = (current_user.brand_id is not None) and (current_user.store_id is None)
        
        if comment.announcement.brand_id != current_user.current_brand_id:
             abort(403, description="권한이 없습니다.")

        if not is_author and not is_hq_admin:
            abort(403, description="댓글 삭제 권한이 없습니다.")
            
        announcement_id = comment.announcement_id
        db.session.delete(comment)
        db.session.commit()
        flash("댓글이 삭제되었습니다.", "success")
        
        return redirect(url_for('ui.announcement_detail', id=announcement_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting comment: {e}")
        flash(f"댓글 삭제 중 오류 발생: {e}", "error")
        return redirect(url_for('ui.announcement_list'))
