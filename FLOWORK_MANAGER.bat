@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul
cls

:: ============================================================
:: [설정] 서버 접속 정보 수정
:: ============================================================
set SERVER_IP=212.47.68.72
set USER=root
set PROJECT_DIR=~/flowork
:: ============================================================

:MAIN_MENU
cls
echo.
echo ==========================================================
echo        FLOWORK 서버 매니저 (v4.1 Fix & Init)
echo        Target: %SERVER_IP% (%USER%)
echo ==========================================================
echo.
echo  [1] 🚀  배포 및 설정 (Deploy & Config)
echo       - 코드 업데이트, .env 파일 업로드
echo.
echo  [2] 💾  데이터베이스 관리 (DB & Migration)
echo       - 마이그레이션, 스키마 적용, 백업/복구
echo.
echo  [3] 📊  모니터링 및 로그 (Logs & Health)
echo       - 실시간 앱 로그, 서버 헬스 체크
echo.
echo  [4] ⚙️  시스템 관리 (System & Docker)
echo       - 자동 로그인, 디스크 정리, 재부팅
echo.
echo  [0] 종료
echo.
echo ==========================================================
set /p choice="선택하세요 (번호 입력): "

if "%choice%"=="1" goto DEPLOY_MENU
if "%choice%"=="2" goto DB_MENU
if "%choice%"=="3" goto MONITOR_MENU
if "%choice%"=="4" goto SYSTEM_MENU
if "%choice%"=="0" exit
goto MAIN_MENU

:: ============================================================
:: [1] 배포 및 설정 메뉴
:: ============================================================
:DEPLOY_MENU
cls
echo.
echo ==========================================================
echo           🚀 배포 및 설정 관리
echo ==========================================================
echo.
echo  [1] 스마트 배포 (Git Pull + Rebuild) ★필수
echo      - 코드 변경사항 반영 및 라이브러리 설치 (재시작)
echo.
echo  [2] 🔒 .env 환경변수 파일 업로드 ★필수
echo      - PC의 .env 파일을 서버로 전송합니다.
echo.
echo  [3] 🧹 캐시 초기화 재배포 (Clean Deploy)
echo      - 빌드 캐시 삭제 후 처음부터 다시 빌드
echo.
echo  [0] 메인 메뉴로
echo.
echo ==========================================================
set /p d_choice="선택: "

if "%d_choice%"=="1" goto DEPLOY_SMART
if "%d_choice%"=="2" goto UPLOAD_ENV
if "%d_choice%"=="3" goto DEPLOY_CLEAN
if "%d_choice%"=="0" goto MAIN_MENU
goto DEPLOY_MENU

:DEPLOY_SMART
echo.
echo [서버] Git Pull 및 컨테이너 재빌드 중...
ssh %USER%@%SERVER_IP% "cd %PROJECT_DIR% && git pull origin main && docker compose up -d --build"
echo.
echo ✅ 배포 완료.
pause
goto DEPLOY_MENU

:UPLOAD_ENV
echo.
if not exist ".env" (
    echo ❌ PC의 현재 폴더에 .env 파일이 없습니다. 
    echo    프로젝트 루트에 .env 파일을 생성했는지 확인하세요.
    pause
    goto DEPLOY_MENU
)
echo [PC -> 서버] .env 파일 전송 중...
scp .env %USER%@%SERVER_IP%:%PROJECT_DIR%/.env
echo.
echo ✅ 전송 완료. 반드시 [1]번 '스마트 배포'를 실행하여 적용하세요.
pause
goto DEPLOY_MENU

:DEPLOY_CLEAN
echo.
echo [서버] 컨테이너 중지 및 캐시 삭제 후 재빌드...
ssh %USER%@%SERVER_IP% "cd %PROJECT_DIR% && (docker compose down || true) && git pull origin main && docker builder prune -af && docker compose build --no-cache && docker compose up -d"
echo.
echo ✅ 클린 배포 완료.
pause
goto DEPLOY_MENU


:: ============================================================
:: [2] 데이터베이스 관리 메뉴
:: ============================================================
:DB_MENU
cls
echo.
echo ==========================================================
echo           💾 데이터베이스 관리 (Flask-Migrate)
echo ==========================================================
echo.
echo  [1] 🏁  DB 마이그레이션 초기화 (Init) ★최초 1회
echo      - 'migrations' 폴더를 생성합니다. (처음에만 실행)
echo.
echo  [2] 📝  새 마이그레이션 생성 (Migrate)
echo      - 모델 변경사항을 감지하여 스크립트를 생성합니다.
echo.
echo  [3] 🏗️  DB 변경사항 적용 (Upgrade)
echo      - 생성된 마이그레이션을 DB에 실제 반영합니다.
echo.
echo  [4] 📥  통합 백업 (DB + 이미지)
echo      - 현재 상태를 PC 바탕화면으로 백업합니다.
echo.
echo  [5] ♻️  DB 전체 초기화 (Hard Reset)
echo      - [주의] 모든 데이터를 삭제하고 테이블을 재생성합니다.
echo.
echo  [0] 메인 메뉴로
echo.
echo ==========================================================
set /p db_choice="선택: "

if "%db_choice%"=="1" goto DB_INIT_MIGRATE
if "%db_choice%"=="2" goto DB_MIGRATE
if "%db_choice%"=="3" goto DB_UPGRADE
if "%db_choice%"=="4" goto DB_BACKUP
if "%db_choice%"=="5" goto DB_RESET
if "%db_choice%"=="0" goto MAIN_MENU
goto DB_MENU

:DB_INIT_MIGRATE
echo.
echo [서버] 마이그레이션 저장소 초기화 (flask db init)...
ssh %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker compose exec web flask --app run.py db init"
echo.
echo ✅ 초기화 완료. (이미 존재한다는 에러가 나면 정상입니다)
pause
goto DB_MENU

:DB_MIGRATE
echo.
set /p msg="마이그레이션 메시지 (예: add_column): "
echo [서버] 마이그레이션 스크립트 생성 중...
ssh %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker compose exec web flask --app run.py db migrate -m '%msg%'"
echo.
echo ✅ 생성 완료. 반드시 '3번 DB 변경사항 적용'을 실행해야 반영됩니다.
pause
goto DB_MENU

:DB_UPGRADE
echo.
echo [서버] DB 스키마 업그레이드 (flask db upgrade)...
ssh %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker compose exec web flask --app run.py db upgrade"
echo.
echo ✅ 적용 완료.
pause
goto DB_MENU

:DB_BACKUP
echo.
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TS=%datetime:~0,4%%datetime:~4,2%%datetime:~6,2%_%datetime:~8,2%%datetime:~10,2%
set BACKUP_PATH=%USERPROFILE%\Desktop\FLOWORK_BACKUP_%TS%
mkdir "%BACKUP_PATH%"

echo [1/3] DB 덤프 생성...
ssh %USER%@%SERVER_IP% "docker exec flowork_db pg_dump -U flowork_user flowork_db > ~/flowork/backup.sql"

echo [2/3] 이미지 압축...
ssh %USER%@%SERVER_IP% "tar -czf ~/flowork/images.tar.gz -C ~/flowork/flowork/static product_images"

echo [3/3] PC로 다운로드...
scp %USER%@%SERVER_IP%:~/flowork/backup.sql "%BACKUP_PATH%\backup.sql"
scp %USER%@%SERVER_IP%:~/flowork/images.tar.gz "%BACKUP_PATH%\images.tar.gz"

echo.
echo ✅ 백업 완료: %BACKUP_PATH%
pause
goto DB_MENU

:DB_RESET
echo.
echo 🚨 경고: 모든 데이터가 영구적으로 삭제됩니다!
set /p confirm="정말 초기화하시겠습니까? (yes/no): "
if not "%confirm%"=="yes" goto DB_MENU

echo [서버] DB 초기화 (init-db command)...
ssh %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker compose exec web flask --app run.py init-db"
echo.
echo ✅ 초기화 완료.
pause
goto DB_MENU


:: ============================================================
:: [3] 모니터링 및 로그 메뉴
:: ============================================================
:MONITOR_MENU
cls
echo.
echo ==========================================================
echo           📊 모니터링 및 로그
echo ==========================================================
echo.
echo  [1] 📜 실시간 앱 로그 (File Tail)
echo      - 파일로 기록되는 상세 로그 확인 (logs/flowork.log)
echo.
echo  [2] 🐳 컨테이너 로그 (Stdout)
echo      - Gunicorn/Docker 표준 출력 로그 확인
echo.
echo  [3] 🏥 서버 헬스 체크 (Health Check)
echo      - API 응답 상태 확인 (/health)
echo.
echo  [4] 📈 리소스 점검 (Top)
echo      - CPU/메모리 사용량 확인
echo.
echo  [0] 메인 메뉴로
echo.
echo ==========================================================
set /p m_choice="선택: "

if "%m_choice%"=="1" (
    echo [Ctrl+C로 종료하세요]
    ssh -t %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker compose exec web tail -f logs/flowork.log"
    goto MONITOR_MENU
)
if "%m_choice%"=="2" (
    ssh -t %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker compose logs -f --tail=100 web"
    goto MONITOR_MENU
)
if "%m_choice%"=="3" (
    echo.
    echo [Health Check]
    ssh %USER%@%SERVER_IP% "curl -s http://localhost:5000/health | python3 -m json.tool"
    echo.
    pause
    goto MONITOR_MENU
)
if "%m_choice%"=="4" (
    ssh -t %USER%@%SERVER_IP% "docker stats --no-stream"
    pause
    goto MONITOR_MENU
)
if "%m_choice%"=="0" goto MAIN_MENU
goto MONITOR_MENU


:: ============================================================
:: [4] 시스템 관리 메뉴
:: ============================================================
:SYSTEM_MENU
cls
echo.
echo ==========================================================
echo           ⚙️ 시스템 관리
echo ==========================================================
echo.
echo  [1] 🔑 SSH 자동 로그인 설정
echo      - 인증키 생성 및 서버 등록
echo.
echo  [2] 🧹 도커 시스템 정리 (Prune)
echo      - 사용하지 않는 이미지/볼륨 삭제 (디스크 확보)
echo.
echo  [3] 🔄 서버 재부팅
echo      - VPS 자체를 재시작
echo.
echo  [0] 메인 메뉴로
echo.
echo ==========================================================
set /p s_choice="선택: "

if "%s_choice%"=="1" goto AUTO_SSH
if "%s_choice%"=="2" goto DOCKER_PRUNE
if "%s_choice%"=="3" goto SERVER_REBOOT
if "%s_choice%"=="0" goto MAIN_MENU
goto SYSTEM_MENU

:AUTO_SSH
echo.
if not exist "%USERPROFILE%\.ssh\id_rsa.pub" (
    echo 키 생성 중...
    ssh-keygen -t rsa -b 4096 -f "%USERPROFILE%\.ssh\id_rsa" -N ""
)
echo 키 전송 중 (비밀번호 입력 필요)...
type "%USERPROFILE%\.ssh\id_rsa.pub" | ssh %USER%@%SERVER_IP% "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
echo.
echo ✅ 설정 완료.
pause
goto SYSTEM_MENU

:DOCKER_PRUNE
echo.
echo [서버] 사용하지 않는 도커 데이터 정리 중...
ssh %USER%@%SERVER_IP% "docker system prune -a -f --volumes"
echo.
echo ✅ 정리 완료.
pause
goto SYSTEM_MENU

:SERVER_REBOOT
echo.
echo 🔄 서버를 재부팅합니다. 잠시 연결이 끊어집니다.
ssh %USER%@%SERVER_IP% "reboot"
pause
goto SYSTEM_MENU