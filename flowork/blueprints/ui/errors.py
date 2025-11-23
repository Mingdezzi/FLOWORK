from flask import render_template
from . import ui_bp
from ...extensions import db
import traceback

# @ui_bp.app_errorhandler를 사용하면 블루프린트뿐만 아니라 앱 전체의 에러를 잡습니다.

@ui_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('404.html', 
                           error_description=getattr(error, 'description', '페이지를 찾을 수 없습니다.')), 404

@ui_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    print(f"Internal Server Error: {error}")
    traceback.print_exc() 
    return render_template('500.html', 
                           error_message=str(error)), 500

@ui_bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('403.html',
                           error_description=getattr(error, 'description', '이 작업에 대한 권한이 없습니다.')), 403