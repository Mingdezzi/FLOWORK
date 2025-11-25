import os
import time
from dotenv import load_dotenv

load_dotenv()

class Config:
    os.environ['TZ'] = os.getenv('TZ', 'Asia/Seoul')
    try:
        time.tzset()
    except AttributeError:
        pass

    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY가 .env 파일에 설정되어야 합니다.")
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    FLOWORK_DIR = os.path.join(BASE_DIR, 'flowork')
    
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL이 .env 파일에 설정되어야 합니다.")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = '/tmp'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 30,
        'max_overflow': 60,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 10
        }
    }

    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
    
    # [신규] Celery 워커 메모리 누수 방지 설정
    # 워커 프로세스가 50개의 작업을 처리하면 자동으로 재시작되어 메모리를 초기화합니다.
    CELERY_WORKER_MAX_TASKS_PER_CHILD = 50

    # Caching 설정 (Redis)
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = CELERY_BROKER_URL
    CACHE_DEFAULT_TIMEOUT = 300
