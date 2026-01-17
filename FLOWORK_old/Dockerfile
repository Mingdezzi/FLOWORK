# (*** 수정: 3.11-slim 단일 스테이지로 변경 ***)
FROM python:3.11-slim

WORKDIR /app

# (*** apt-get 및 builder 스테이지 모두 제거 ***)

# requirements.txt 복사 및 파이썬 라이브러리 설치
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 전체 복사
COPY . .

# (*** 수정: --preload 옵션 추가! ***)
# @app.before_request가 DB 생성을 처리하므로 CMD에서는 gunicorn만 실행합니다.
CMD gunicorn --workers 1 --bind 0.0.0.0:$PORT --preload app:app