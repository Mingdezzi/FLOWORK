from flask import request, jsonify
from flask_login import login_required, current_user
from flowork.modules.network import network_bp
from flowork.modules.network.services import create_suggestion_service, delete_suggestion_service, send_mail_service
from flowork.models import db, SuggestionComment, StoreMail

@network_bp.route('/api/suggestions', methods=['POST'])
@login_required
def api_create_sugg():
    d = request.json
    ok, msg = create_suggestion_service(current_user.current_brand_id, current_user.store_id, d.get('title'), d.get('content'), d.get('is_private'))
    if ok: return jsonify({'status':'success', 'message':'등록 완료'})
    return jsonify({'status':'error', 'message':msg}), 500

@network_bp.route('/api/suggestions/<int:sid>/comment', methods=['POST'])
@login_required
def api_add_comment(sid):
    c = request.json.get('content')
    if not c: return jsonify({'status':'error'}), 400
    db.session.add(SuggestionComment(suggestion_id=sid, user_id=current_user.id, content=c))
    db.session.commit()
    return jsonify({'status':'success'})

@network_bp.route('/api/suggestions/<int:sid>', methods=['DELETE'])
@login_required
def api_del_sugg(sid):
    ok, msg = delete_suggestion_service(sid, current_user.current_brand_id, current_user)
    if ok: return jsonify({'status':'success'})
    return jsonify({'status':'error', 'message':msg}), 403

@network_bp.route('/api/mails', methods=['POST'])
@login_required
def api_send_mail():
    d = request.json
    tgt = d.get('target_store_id')
    rid = int(tgt) if tgt != 'HQ' else None
    ok, msg = send_mail_service(current_user.current_brand_id, current_user.store_id, rid, d.get('title'), d.get('content'))
    if ok: return jsonify({'status':'success', 'message':'발송 완료'})
    return jsonify({'status':'error', 'message':msg}), 500

@network_bp.route('/api/mails/<int:mid>', methods=['DELETE'])
@login_required
def api_del_mail(mid):
    m = StoreMail.query.filter_by(id=mid, brand_id=current_user.current_brand_id).first()
    if not m: return jsonify({'status':'error'}), 404
    sid = current_user.store_id
    if m.sender_store_id != sid and m.receiver_store_id != sid: return jsonify({'status':'error'}), 403
    db.session.delete(m)
    db.session.commit()
    return jsonify({'status':'success'})