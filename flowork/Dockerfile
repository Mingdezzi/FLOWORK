# 멀티 스테이지 빌드로 최적화
FROM python:3.11-slim as builder

WORKDIR /app

# 1. 의존성만 먼저 복사 (캐시 활용)
COPY requirements.txt .

# 2. 의존성 설치 (변경 시에만 재실행)
RUN pip install --no-cache-dir -r requirements.txt

# 최종 이미지
FROM python:3.11-slim

WORKDIR /app

# 3. builder에서 설치된 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 4. 앱 코드 복사 (이것만 변경 시 캐시된 레이어 활용)
COPY . .

# 5. Gunicorn CMD (worker=1 유지하여 APScheduler 중복 실행 방지)
CMD gunicorn --workers 1 --bind 0.0.0.0:$PORT --timeout 120 run:app