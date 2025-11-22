from flowork.models import db, Announcement, Suggestion, SuggestionComment, StoreMail
from datetime import datetime

def create_announcement_service(brand_id, title, content):
    try:
        a = Announcement(brand_id=brand_id, title=title, content=content)
        db.session.add(a)
        db.session.commit()
        return True, a
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def delete_announcement_service(ann_id, brand_id):
    try:
        a = Announcement.query.filter_by(id=ann_id, brand_id=brand_id).first()
        if not a: return False, "공지 없음"
        db.session.delete(a)
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def create_suggestion_service(brand_id, store_id, title, content, is_private):
    try:
        s = Suggestion(brand_id=brand_id, store_id=store_id, title=title, content=content, is_private=is_private)
        db.session.add(s)
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def delete_suggestion_service(s_id, brand_id, user):
    try:
        s = Suggestion.query.filter_by(id=s_id, brand_id=brand_id).first()
        if not s: return False, "글 없음"
        is_auth = (s.store_id == user.store_id) if user.store_id else (s.store_id is None)
        if not is_auth and not user.is_admin: return False, "권한 없음"
        db.session.delete(s)
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def send_mail_service(brand_id, sender_id, receiver_id, title, content):
    try:
        m = StoreMail(brand_id=brand_id, sender_store_id=sender_id, receiver_store_id=receiver_id, title=title, content=content)
        db.session.add(m)
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)