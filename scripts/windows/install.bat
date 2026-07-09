@echo off
chcp 65001 > nul
title NCVS 초기 설치

echo ============================================
echo  NCVS 초기 설치 (최초 1회만 실행)
echo ============================================
echo.

:: ── 포트 사용 확인 ──────────────────────────────────────────
netstat -an | findstr ":8000 " > nul 2>&1
if not errorlevel 1 (
    echo [경고] 포트 8000이 이미 사용 중입니다.
    echo        다른 프로그램을 종료 후 다시 실행하세요.
    pause
    exit /b 1
)
netstat -an | findstr ":3000 " > nul 2>&1
if not errorlevel 1 (
    echo [경고] 포트 3000이 이미 사용 중입니다.
    echo        다른 프로그램을 종료 후 다시 실행하세요.
    pause
    exit /b 1
)

:: ── Python pip 패키지 설치 ──────────────────────────────────
echo [1/4] Python 패키지 설치 중...
python\python.exe -m pip install --no-index --find-links=wheels -r backend\requirements-windows.txt --quiet
if errorlevel 1 (
    echo [ERROR] 패키지 설치 실패
    pause
    exit /b 1
)
echo [1/4] 완료

:: ── data 디렉터리 생성 ──────────────────────────────────────
echo [2/4] 데이터 디렉터리 생성...
if not exist "data" mkdir data
echo [2/4] 완료

:: ── Alembic DB 초기화 (SQLite 파일 + 테이블 생성) ──────────
echo [3/4] DB 초기화 중 (테이블 생성)...
cd backend
..\python\python.exe -m alembic upgrade head
if errorlevel 1 (
    echo [ERROR] DB 초기화 실패
    cd ..
    pause
    exit /b 1
)
cd ..
echo [3/4] 완료

:: ── 관리자 계정 시드 ────────────────────────────────────────
echo [4/4] 초기 계정 생성 중 (admin / admin)...
cd backend
..\python\python.exe -m app.cli.seed admin admin
cd ..
echo [4/4] 완료

:: ── Windows 방화벽 허용 (선택) ──────────────────────────────
echo.
echo [방화벽] 포트 3000, 8000 허용 규칙 추가 시도...
netsh advfirewall firewall add rule name="NCVS Frontend" dir=in action=allow protocol=TCP localport=3000 > nul 2>&1
netsh advfirewall firewall add rule name="NCVS Backend"  dir=in action=allow protocol=TCP localport=8000 > nul 2>&1

echo.
echo ============================================
echo  초기 설치 완료!
echo  기본 계정: admin / admin
echo  이제 start.bat 을 실행하세요.
echo ============================================
pause
