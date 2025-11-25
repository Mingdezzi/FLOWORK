import os
import multiprocessing

# Server Socket
bind = "0.0.0.0:5000"
backlog = 2048

# [최적화] Worker Processes Tuning (6 vCPU, 12GB RAM)
# 공식 권장: (2 x CPU) + 1
# CPU가 6개이므로 13개까지 가능하지만, DB/Redis와 자원을 공유하므로 
# 안전하게 9개로 늘려 처리량을 높입니다.
workers = 9  
worker_class = 'gthread'
threads = 4  # 스레드는 유지하여 I/O 대기 시간 활용

# Timeouts
timeout = 120
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process Naming
proc_name = 'flowork_app'

# Requests (메모리 누수 방지)
max_requests = 2000        # 요청 처리 한도 상향
max_requests_jitter = 100

# Environment
raw_env = [
    "TZ=Asia/Seoul"
]