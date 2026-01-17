import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'wasabi-check-secret-key-fallback')
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    FLOWORK_DIR = os.path.join(BASE_DIR, 'flowork')
    
    # 1. (수정) 기본 DB (상품/재고/주문/설정/공지 모두 포함)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    
    # (삭제) 2. 주문 DB (ORDERS_DATABASE_URL)
    # (삭제) 3. 공지사항 DB (ANNOUNCEMENT_DATABASE_URL)
    # (삭제) 4. 매장정보 DB (STORE_INFO_DATABASE_URL)

    # (삭제) SQLALCHEMY_BINDS 설정 전체 삭제

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = '/tmp'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # (기존) Neon DB 최적화 설정
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,     # Neon의 5분(300초) 타임아웃보다 짧게 설정
        'pool_pre_ping': True,   # 연결 사용 전 유효성 검사
        'pool_size': 2,          # (수정) Render/Neon 무료 플랜 최적화 (기본 2)
        'max_overflow': 3,      # (수정) Render/Neon 무료 플랜 최적화 (최대 3)
        'pool_timeout': 30,      # 풀에서 연결을 기다리는 최대 시간
        'connect_args': {
            'connect_timeout': 10  # 연결 시도 타임아웃 (초)
        }
    }