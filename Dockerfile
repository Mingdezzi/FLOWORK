FROM python:3.11-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

RUN apt-get update && \
    apt-get install -y curl && \
    mkdir -p /app/models && \
    curl -L -o /app/models/u2net.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . .

ENV CUDA_VISIBLE_DEVICES=-1

CMD gunicorn --workers 6 --bind 0.0.0.0:$PORT --timeout 300 run:app