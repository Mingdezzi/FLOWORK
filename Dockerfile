FROM python:3.12-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

# 빌더 이미지에서 패키지 복사
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 필수 시스템 패키지 및 Git 설치 (버전 관리 기능용)
RUN apt-get update && \
    apt-get install -y curl git && \
    mkdir -p /app/models && \
    curl -L -o /app/models/u2net.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . .

# 환경 변수 설정
ENV CUDA_VISIBLE_DEVICES=-1
ENV PYTHONUNBUFFERED=1

# Gunicorn 실행 (설정 파일 사용)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]