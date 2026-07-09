@echo off
chcp 65001 > nul
title NCVS 서버

echo ============================================
echo  NCVS 서버 시작
echo ============================================
echo.

:: ── install.bat 실행 여부 확인 ──────────────────────────────
if not exist "data" (
    echo [ERROR] 초기 설치가 필요합니다.
    echo         install.bat 을 먼저 실행하세요.
    pause
    exit /b 1
)

:: ── 포트 사용 확인 ──────────────────────────────────────────
netstat -an | findstr ":8000 " > nul 2>&1
if not errorlevel 1 (
    echo [경고] 포트 8000이 이미 사용 중입니다.
    echo        stop.bat 실행 후 다시 시도하세요.
    pause
    exit /b 1
)

:: ── 백엔드 시작 (별도 창) ───────────────────────────────────
echo [1/2] 백엔드 시작 중 (http://localhost:8000)...
cd backend
start "NCVS-Backend" /min ..\python\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level warning
cd ..

:: 백엔드 기동 대기
echo        백엔드 초기화 대기 중...
timeout /t 4 /nobreak > nul

:: ── 프론트엔드 시작 (별도 창) ───────────────────────────────
echo [2/2] 프론트엔드 시작 중 (http://localhost:3000)...
set BACKEND_URL=http://localhost:8000
set PORT=3000
set HOSTNAME=0.0.0.0
cd frontend
start "NCVS-Frontend" /min ..\node\node.exe server.js
cd ..

:: 프론트엔드 기동 대기
timeout /t 3 /nobreak > nul

:: ── 브라우저 자동 오픈 ──────────────────────────────────────
start http://localhost:3000

echo.
echo ============================================
echo  서버 실행 중
echo   UI  : http://localhost:3000
echo   API : http://localhost:8000/docs
echo.
echo  로그인: admin / admin
echo  종료 : stop.bat 실행
echo ============================================
