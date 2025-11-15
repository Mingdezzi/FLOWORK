import os
import time

class Config:
    os.environ['TZ'] = 'Asia/Seoul'
    try:
        time.tzset()
    except AttributeError:
        pass

    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY 환경 변수가 설정되어야 합니다.")
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    FLOWORK_DIR = os.path.join(BASE_DIR, 'flowork')
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL 환경 변수가 설정되어야 합니다.")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = '/tmp'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
        'pool_size': 3,
        'max_overflow': 5,
        'pool_timeout': 30,
        'connect_args': {
            'connect_timeout': 10
        }
    }