from flask import render_template, request, abort, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_
from flowork.models import db, Suggestion, StoreMail, Store
from . import ui_bp

@ui_bp.route('/network/suggestions')
@login_required
def suggestion_list():
    page = request.args.get('page', 1, type=int)
    query = Suggestion.query.filter_by(brand_id=current_user.current_brand_id)
    
    # 비공개 글 처리: 본인 글이거나 관리자인 경우만 볼 수 있게 하거나, 리스트엔 띄우되 내용은 숨김
    # 여기서는 리스트에 띄우고 템플릿에서 자물쇠 표시
    
    pagination = query.order_by(Suggestion.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('suggestion_list.html', active_page='suggestion', pagination=pagination)

@ui_bp.route('/network/suggestions/<id>')
@login_required
def suggestion_detail(id):
    if id == 'new':
        return render_template('suggestion_detail.html', active_page='suggestion', item=None)
        
    item = Suggestion.query.filter_by(id=int(id), brand_id=current_user.current_brand_id).first_or_404()
    
    # 비공개 글 권한 체크
    if item.is_private:
        is_author = (item.store_id == current_user.store_id)
        # 본사 관리자(store_id=None)는 모든 글 조회 가능
        is_admin = (current_user.store_id is None)
        if not is_author and not is_admin:
            abort(403, description="비공개 글입니다.")
            
    return render_template('suggestion_detail.html', active_page='suggestion', item=item)

@ui_bp.route('/network/mail')
@login_required
def mail_box():
    box_type = request.args.get('type', 'inbox') # inbox / sent
    page = request.args.get('page', 1, type=int)
    
    my_store_id = current_user.store_id # None이면 본사
    
    if box_type == 'inbox':
        query = StoreMail.query.filter_by(
            brand_id=current_user.current_brand_id,
            receiver_store_id=my_store_id
        )
    else:
        query = StoreMail.query.filter_by(
            brand_id=current_user.current_brand_id,
            sender_store_id=my_store_id
        )
        
    pagination = query.order_by(StoreMail.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('mail_box.html', active_page='mail', pagination=pagination, box_type=box_type)

@ui_bp.route('/network/mail/compose')
@login_required
def mail_compose():
    # 수신처 목록 (본사 + 타 매장)
    stores = Store.query.filter(
        Store.brand_id == current_user.current_brand_id,
        Store.is_active == True
    )
    if current_user.store_id:
        stores = stores.filter(Store.id != current_user.store_id)
        
    return render_template('mail_compose.html', active_page='mail', stores=stores.all())

@ui_bp.route('/network/mail/<int:id>')
@login_required
def mail_detail(id):
    mail = StoreMail.query.filter_by(id=id, brand_id=current_user.current_brand_id).first_or_404()
    
    # 권한 체크
    is_sender = (mail.sender_store_id == current_user.store_id)
    is_receiver = (mail.receiver_store_id == current_user.store_id)
    if not is_sender and not is_receiver:
        abort(403)
        
    # 읽음 처리 (수신자가 조회 시)
    if is_receiver and not mail.is_read:
        mail.is_read = True
        db.session.commit()
        
    return render_template('mail_detail.html', active_page='mail', mail=mail, is_sender=is_sender)