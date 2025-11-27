FROM python:3.11-slim

WORKDIR /app

# 필수 시스템 패키지 설치
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gunicorn으로 실행 (프로덕션용)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]