import os

# Server Socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker Processes (6 vCPU, 12GB RAM 최적화)
# 공식: (2 x CPU) + 1 이지만, Celery와 DB가 같은 서버에 있으므로 워커 수를 조절함
workers = 5 
worker_class = 'gthread'
threads = 4

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
max_requests = 1000
max_requests_jitter = 50

# Environment
raw_env = [
    "TZ=Asia/Seoul"
]