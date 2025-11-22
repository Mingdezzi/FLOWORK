from flask import render_template
from . import main_bp
from flowork.models import db

@main_bp.app_errorhandler(404)
def not_found(e): return render_template('404.html', error_description=getattr(e, 'description', 'Not Found')), 404

@main_bp.app_errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_template('500.html', error_message=str(e)), 500

@main_bp.app_errorhandler(403)
def forbidden(e): return render_template('403.html', error_description=getattr(e, 'description', 'Forbidden')), 403