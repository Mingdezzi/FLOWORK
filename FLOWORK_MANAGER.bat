@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul
cls

:: ====================================================
:: [설정] 서버 정보
:: ====================================================
set SERVER_IP=212.47.68.72
set USER=root
set PROJECT_DIR=~/flowork
:: ====================================================

:MAIN_MENU
cls
echo.
echo ======================================================
echo        FLOWORK 서버 매니저 (v3.1 Auto-Login)
echo        Target: %SERVER_IP% (%USER%)
echo ======================================================
echo.
echo  [1] 🚀  배포 및 업데이트 (Deployment)
echo       - 스마트 업데이트, 코드 재배포
echo.
echo  [2] 💾  데이터 및 백업 (Data & Backup)
echo       - 백업, 복구, DB 초기화, 스키마 업데이트
echo.
echo  [3] 📊  모니터링 및 로그 (Monitor & Logs)
echo       - 로그 보기, 서버 상태 점검
echo.
echo  [4] ⚙️  시스템 관리 (System Admin)
echo       - ★자동 로그인 설정★, Docker 설치, 재부팅
echo.
echo  [0] 종료
echo.
echo ======================================================
set /p choice="선택하세요 (번호 입력): "

if "%choice%"=="1" goto DEPLOY_MENU
if "%choice%"=="2" goto DATA_MENU
if "%choice%"=="3" goto LOG_MENU
if "%choice%"=="4" goto SYSTEM_MENU
if "%choice%"=="0" exit
goto MAIN_MENU

:: ====================================================
:: 1. 배포 메뉴
:: ====================================================
:DEPLOY_MENU
cls
echo.
echo ======================================================
echo           🚀 배포 및 업데이트
echo ======================================================
echo.
echo  [1] 스마트 업데이트 (Git Pull + 재시작)
echo      - 변경된 코드만 반영 (데이터 유지)
echo.
echo  [2] 코드 캐시 초기화 (Re-deploy)
echo      - 코드가 꼬였을 때 재빌드 (DB 유지)
echo.
echo  [0] 뒤로 가기
echo.
echo ======================================================
set /p d_choice="선택: "

if "%d_choice%"=="1" goto DEPLOY_SMART
if "%d_choice%"=="2" goto DEPLOY_RESET
if "%d_choice%"=="0" goto MAIN_MENU
goto DEPLOY_MENU

:DEPLOY_SMART
echo.
echo [서버] 업데이트 진행 중...
ssh %USER%@%SERVER_IP% "cd %PROJECT_DIR% && git pull origin main && docker compose up -d --build"
echo.
echo ✅ 완료.
pause
goto DEPLOY_MENU

:DEPLOY_RESET
echo.
echo [서버] 캐시 초기화 및 재배포 중...
ssh %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker compose down && docker builder prune -af && git pull origin main && docker compose build --no-cache && docker compose up -d"
echo.
echo ✅ 완료.
pause
goto DEPLOY_MENU

:: ====================================================
:: 2. 데이터 메뉴
:: ====================================================
:DATA_MENU
cls
echo.
echo ======================================================
echo           💾 데이터 관리
echo ======================================================
echo.
echo  [1] 📤  통합 백업 (DB + 이미지) ★추천
echo      - 바탕화면에 DB와 이미지를 저장합니다.
echo.
echo  [2] 🏗️  DB 스키마 업데이트 (Update DB)
echo      - 데이터는 유지하고 테이블 구조만 갱신합니다.
echo.
echo  [3] ♻️   DB 테이블 초기화 (Init DB)
echo      - 기존 데이터를 삭제하고 빈 테이블을 만듭니다.
echo.
echo  [4] 🚑  데이터 복구 (Restore)
echo      - PC의 최신 백업 파일을 서버로 복원합니다.
echo.
echo  [0] 뒤로 가기
echo.
echo ======================================================
set /p data_choice="선택: "

if "%data_choice%"=="1" goto RUN_BACKUP
if "%data_choice%"=="2" goto DB_SCHEMA_UPDATE
if "%data_choice%"=="3" goto DB_INIT
if "%data_choice%"=="4" goto RUN_RESTORE
if "%data_choice%"=="0" goto MAIN_MENU
goto DATA_MENU

:DB_SCHEMA_UPDATE
echo.
echo [서버] DB 스키마 업데이트 중...
ssh %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker exec flowork_app flask --app run.py update-db"
pause
goto DATA_MENU

:DB_INIT
echo.
echo [서버] DB 테이블 초기화 중...
ssh %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker exec flowork_app flask --app run.py init-db"
pause
goto DATA_MENU

:: ====================================================
:: 3. 로그 메뉴
:: ====================================================
:LOG_MENU
cls
echo.
echo ======================================================
echo           📊 로그 및 상태
echo ======================================================
echo.
echo  [1] 전체 로그 보기
echo  [2] 웹앱(App) 로그만 보기
echo  [3] DB 로그만 보기
echo  [4] 서버 상태 점검 (디스크/메모리)
echo  [0] 뒤로 가기
echo.
echo ======================================================
set /p l_choice="선택: "

if "%l_choice%"=="1" (
    ssh -t %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker compose logs -f --tail=50"
    goto LOG_MENU
)
if "%l_choice%"=="2" (
    ssh -t %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker compose logs -f --tail=50 web"
    goto LOG_MENU
)
if "%l_choice%"=="3" (
    ssh -t %USER%@%SERVER_IP% "cd %PROJECT_DIR% && docker compose logs -f --tail=50 db"
    goto LOG_MENU
)
if "%l_choice%"=="4" (
    echo.
    echo [서버] 상태 점검 결과:
    echo ---------------------------------------------------
    ssh %USER%@%SERVER_IP% "echo '[DISK]' && df -h | grep '/$' && echo '' && echo '[MEMORY]' && free -h && echo '' && echo '[CONTAINERS]' && docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    echo ---------------------------------------------------
    pause
    goto LOG_MENU
)
if "%l_choice%"=="0" goto MAIN_MENU
goto LOG_MENU

:: ====================================================
:: 4. 시스템 메뉴
:: ====================================================
:SYSTEM_MENU
cls
echo.
echo ======================================================
echo           ⚙️ 시스템 관리
echo ======================================================
echo.
echo  [1] 🔑  자동 로그인 설정 (SSH Key 등록) ★필수
echo      - 최초 1회만 비밀번호를 입력하면, 이후 자동 접속됩니다.
echo.
echo  [2] 🔧  Docker 기초 설치 (수동 모드)
echo  [3] ⚡  SSH 접속 오류 해결 (Key Reset)
echo  [4] 🔄  서버 재부팅
echo  [0] 뒤로 가기
echo.
echo ======================================================
set /p s_choice="선택: "

if "%s_choice%"=="1" goto SETUP_AUTO_LOGIN
if "%s_choice%"=="2" goto DOCKER_INSTALL
if "%s_choice%"=="3" goto SSH_RESET
if "%s_choice%"=="4" goto REBOOT
if "%s_choice%"=="0" goto MAIN_MENU
goto SYSTEM_MENU

:SETUP_AUTO_LOGIN
echo.
echo [1/2] PC에 SSH 인증키가 있는지 확인합니다...
if not exist "%USERPROFILE%\.ssh\id_rsa.pub" (
    echo 키가 없어서 새로 생성합니다...
    ssh-keygen -t rsa -b 4096 -f "%USERPROFILE%\.ssh\id_rsa" -N ""
) else (
    echo 이미 인증키가 존재합니다. 기존 키를 사용합니다.
)

echo.
echo [2/2] 서버에 키를 등록합니다. (마지막으로 비밀번호를 입력하세요!)
echo.
type "%USERPROFILE%\.ssh\id_rsa.pub" | ssh %USER%@%SERVER_IP% "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"

if %errorlevel% equ 0 (
    echo.
    echo ✅ 설정 완료! 이제부터 비밀번호 없이 접속됩니다.
) else (
    echo.
    echo ❌ 설정 실패. 비밀번호가 틀렸거나 서버 접속에 실패했습니다.
)
pause
goto SYSTEM_MENU

:DOCKER_INSTALL
echo.
echo [서버] Docker 및 필수 구성요소 설치 시작...
ssh %USER%@%SERVER_IP% "apt-get update && apt-get install -y ca-certificates curl gnupg git && install -m 0755 -d /etc/apt/keyrings && curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && chmod a+r /etc/apt/keyrings/docker.asc && echo 'deb [arch='$(dpkg --print-architecture)' signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu '$(lsb_release -cs)' stable' | tee /etc/apt/sources.list.d/docker.list > /dev/null && apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin && git clone https://github.com/mingdezzi/flowork.git %PROJECT_DIR% || echo 'Repo exists'"
echo.
echo ✅ 설치 완료.
pause
goto SYSTEM_MENU

:SSH_RESET
ssh-keygen -R %SERVER_IP%
echo.
echo ✅ SSH 키 초기화 완료. 다시 접속해보세요.
pause
goto SYSTEM_MENU

:REBOOT
ssh %USER%@%SERVER_IP% "reboot"
echo.
echo 🔄 재부팅 명령 전송 완료. 잠시 후 접속하세요.
pause
goto SYSTEM_MENU

:: ====================================================
:: [백업 기능]
:: ====================================================
:RUN_BACKUP
echo.
set YEAR=%date:~0,4%
set MONTH=%date:~5,2%
set DAY=%date:~8,2%
set HOUR=%time:~0,2%
set MIN=%time:~3,2%
set HOUR=%HOUR: =0%

set BACKUP_FOLDER=%USERPROFILE%\Desktop\FLOWORK_BACKUP_%YEAR%%MONTH%%DAY%_%HOUR%%MIN%
mkdir "%BACKUP_FOLDER%"

echo [1/3] DB 백업 생성 중...
ssh %USER%@%SERVER_IP% "docker exec flowork_db pg_dump -U flowork_user flowork_db > ~/flowork/backup_db.sql"

echo [2/3] 이미지 폴더 압축 중...
ssh %USER%@%SERVER_IP% "tar -czf ~/flowork/images.tar.gz -C ~/flowork/flowork/static product_images"

echo [3/3] PC로 다운로드 중...
scp %USER%@%SERVER_IP%:~/flowork/backup_db.sql "%BACKUP_FOLDER%\backup_db.sql"
scp %USER%@%SERVER_IP%:~/flowork/images.tar.gz "%BACKUP_FOLDER%\images.tar.gz"

echo.
echo ✅ 백업 완료: %BACKUP_FOLDER%
pause
goto DATA_MENU

:RUN_RESTORE
echo.
echo ⚠️ 주의: 바탕화면의 가장 최신 'FLOWORK_BACKUP_...' 폴더를 찾아 복구합니다.
echo.
set /p confirm="정말 복구하시겠습니까? (y/n): "
if not "%confirm%"=="y" goto DATA_MENU

:: 최신 백업 폴더 찾기 (PowerShell 활용)
for /f "delims=" %%i in ('powershell -Command "Get-ChildItem -Path ([System.Environment]::GetFolderPath('Desktop')) -Directory -Filter 'FLOWORK_BACKUP_*' | Sort-Object CreationTime -Descending | Select-Object -First 1 | Select-Object -ExpandProperty FullName"') do set LATEST_BACKUP=%%i

if "%LATEST_BACKUP%"=="" (
    echo ❌ 바탕화면에서 백업 폴더를 찾을 수 없습니다.
    pause
    goto DATA_MENU
)

echo 📂 복구 대상: %LATEST_BACKUP%

if exist "%LATEST_BACKUP%\backup_db.sql" (
    echo.
    echo [1/2] DB 복구 중...
    scp "%LATEST_BACKUP%\backup_db.sql" %USER%@%SERVER_IP%:~/flowork/backup_db.sql
    ssh -t %USER%@%SERVER_IP% "cat ~/flowork/backup_db.sql | docker exec -i flowork_db psql -U flowork_user flowork_db"
)

if exist "%LATEST_BACKUP%\images.tar.gz" (
    echo.
    echo [2/2] 이미지 복구 중...
    scp "%LATEST_BACKUP%\images.tar.gz" %USER%@%SERVER_IP%:~/flowork/images.tar.gz
    ssh %USER%@%SERVER_IP% "tar -xzf ~/flowork/images.tar.gz -C ~/flowork/flowork/static"
)

echo.
echo ✅ 복구 완료!
pause
goto DATA_MENU