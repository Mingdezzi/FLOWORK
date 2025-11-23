import traceback
from flowork.extensions import db
from flowork.models import Suggestion, SuggestionComment, StoreMail

class NetworkService:
    @staticmethod
    def create_suggestion(brand_id, store_id, title, content, is_private):
        try:
            s = Suggestion(
                brand_id=brand_id,
                store_id=store_id, # None이면 본사
                title=title,
                content=content,
                is_private=is_private
            )
            db.session.add(s)
            db.session.commit()
            return {'status': 'success', 'message': '건의사항이 등록되었습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def add_comment(suggestion_id, user_id, content):
        try:
            c = SuggestionComment(suggestion_id=suggestion_id, user_id=user_id, content=content)
            db.session.add(c)
            db.session.commit()
            return {'status': 'success', 'message': '댓글 등록 완료'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def delete_suggestion(suggestion_id, brand_id, user):
        try:
            s = Suggestion.query.filter_by(id=suggestion_id, brand_id=brand_id).first()
            if not s: return {'status': 'error', 'message': '게시글 없음'}
            
            # 권한 체크: 본인 글이거나 관리자만 삭제 가능
            is_author = (s.store_id == user.store_id) if user.store_id else (s.store_id is None)
            if not is_author and not user.is_admin:
                return {'status': 'error', 'message': '삭제 권한이 없습니다.'}
                
            db.session.delete(s)
            db.session.commit()
            return {'status': 'success', 'message': '삭제되었습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def send_mail(brand_id, sender_store_id, target_store_id, title, content):
        try:
            receiver_id = None
            if target_store_id != 'HQ':
                try:
                    receiver_id = int(target_store_id)
                except:
                    return {'status': 'error', 'message': '수신처 오류'}
            
            mail = StoreMail(
                brand_id=brand_id,
                sender_store_id=sender_store_id,
                receiver_store_id=receiver_id,
                title=title,
                content=content
            )
            db.session.add(mail)
            db.session.commit()
            return {'status': 'success', 'message': '메일이 발송되었습니다.'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def delete_mail(mail_id, brand_id, user_store_id):
        try:
            mail = StoreMail.query.filter_by(id=mail_id, brand_id=brand_id).first()
            if not mail: return {'status': 'error', 'message': '메일 없음'}
            
            # 보낸사람이나 받은사람만 삭제 가능
            is_sender = (mail.sender_store_id == user_store_id)
            is_receiver = (mail.receiver_store_id == user_store_id)
            
            if not is_sender and not is_receiver:
                return {'status': 'error', 'message': '권한 없음'}
                
            db.session.delete(mail)
            db.session.commit()
            return {'status': 'success', 'message': '삭제되었습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}