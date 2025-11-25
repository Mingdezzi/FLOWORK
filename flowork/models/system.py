from datetime import datetime
from ..extensions import db

class UpdateLog(db.Model):
    """시스템 업데이트 로그"""
    __tablename__ = 'update_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(50), nullable=False)  # 예: 1.0.1
    title = db.Column(db.String(255), nullable=False)   # 예: 2024-11-25 정기 업데이트
    content = db.Column(db.Text, nullable=True)         # 변경 내역 (자동 생성됨)
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    
    # 어떤 관리자가 업데이트를 기록했는지 (선택)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.relationship('User')