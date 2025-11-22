from flask import render_template, request, abort, redirect, url_for, flash
from flask_login import login_required, current_user
from flowork.modules.network import network_bp
from flowork.models import Announcement, Comment, Suggestion, StoreMail, Store, db
from flowork.modules.network.services import create_announcement_service, delete_announcement_service

@network_bp.route('/announcements')
@login_required
def announcement_list():
    if current_user.is_super_admin: abort(403)
    items = Announcement.query.filter_by(brand_id=current_user.current_brand_id).order_by(Announcement.created_at.desc()).all()
    return render_template('announcements.html', active_page='announcements', announcements=items)

@network_bp.route('/announcement/<id>', methods=['GET', 'POST'])
@login_required
def announcement_detail(id):
    if current_user.is_super_admin: abort(403)
    bid = current_user.current_brand_id
    is_hq = (current_user.brand_id and not current_user.store_id)
    
    item = None
    if id != 'new':
        item = Announcement.query.filter_by(id=int(id), brand_id=bid).first_or_404()
        
    if request.method == 'POST':
        if not is_hq: abort(403)
        t = request.form['title']
        c = request.form['content']
        if id == 'new':
            ok, res = create_announcement_service(bid, t, c)
            if ok: return redirect(url_for('network.announcement_detail', id=res.id))
        else:
            item.title = t
            item.content = c
            db.session.commit()
            return redirect(url_for('network.announcement_detail', id=item.id))
            
    cmts = item.comments.order_by(Comment.created_at).all() if item else []
    return render_template('announcement_detail.html', active_page='announcements', item=item, is_hq_admin=is_hq, comments=cmts)

@network_bp.route('/announcement/delete/<int:id>', methods=['POST'])
@login_required
def delete_announcement(id):
    if current_user.store_id: abort(403)
    ok, msg = delete_announcement_service(id, current_user.current_brand_id)
    if ok: flash("삭제됨", "success")
    return redirect(url_for('network.announcement_list'))

@network_bp.route('/network/suggestions')
@login_required
def suggestion_list():
    pg = request.args.get('page', 1, type=int)
    q = Suggestion.query.filter_by(brand_id=current_user.current_brand_id).order_by(Suggestion.created_at.desc())
    return render_template('suggestion_list.html', active_page='suggestion', pagination=q.paginate(page=pg, per_page=15))

@network_bp.route('/network/suggestions/<id>')
@login_required
def suggestion_detail(id):
    if id == 'new': return render_template('suggestion_detail.html', active_page='suggestion', item=None)
    item = Suggestion.query.filter_by(id=int(id), brand_id=current_user.current_brand_id).first_or_404()
    if item.is_private:
        is_auth = (item.store_id == current_user.store_id)
        is_admin = (current_user.store_id is None)
        if not is_auth and not is_admin: abort(403)
    return render_template('suggestion_detail.html', active_page='suggestion', item=item)

@network_bp.route('/network/mail')
@login_required
def mail_box():
    box = request.args.get('type', 'inbox')
    pg = request.args.get('page', 1, type=int)
    sid = current_user.store_id
    bid = current_user.current_brand_id
    
    if box == 'inbox': q = StoreMail.query.filter_by(brand_id=bid, receiver_store_id=sid)
    else: q = StoreMail.query.filter_by(brand_id=bid, sender_store_id=sid)
    return render_template('mail_box.html', active_page='mail', pagination=q.order_by(StoreMail.created_at.desc()).paginate(page=pg, per_page=15), box_type=box)

@network_bp.route('/network/mail/compose')
@login_required
def mail_compose():
    q = Store.query.filter(Store.brand_id==current_user.current_brand_id, Store.is_active==True)
    if current_user.store_id: q = q.filter(Store.id!=current_user.store_id)
    return render_template('mail_compose.html', active_page='mail', stores=q.all())

@network_bp.route('/network/mail/<int:id>')
@login_required
def mail_detail(id):
    m = StoreMail.query.filter_by(id=id, brand_id=current_user.current_brand_id).first_or_404()
    sid = current_user.store_id
    if m.sender_store_id != sid and m.receiver_store_id != sid: abort(403)
    if m.receiver_store_id == sid and not m.is_read:
        m.is_read = True
        db.session.commit()
    return render_template('mail_detail.html', active_page='mail', mail=m, is_sender=(m.sender_store_id==sid))