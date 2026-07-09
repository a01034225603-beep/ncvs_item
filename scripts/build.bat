@echo off
chcp 65001 > nul
title NCVS 빌드

echo ============================================================
echo  NCVS Windows 인스톨러 빌드
echo  결과물: scripts\Output\NCVS_Setup.exe
echo ============================================================
echo.

:: ── 사전 요구사항 체크 ───────────────────────────────────────────────────────
where python >nul 2>&1 || (echo [ERROR] Python이 설치되어 있지 않습니다. & pause & exit /b 1)
where node   >nul 2>&1 || (echo [ERROR] Node.js가 설치되어 있지 않습니다.  & pause & exit /b 1)
where npm    >nul 2>&1 || (echo [ERROR] npm이 설치되어 있지 않습니다.        & pause & exit /b 1)

:: Inno Setup ISCC 위치 확인
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    echo [ERROR] Inno Setup 6이 설치되어 있지 않습니다.
    echo         https://jrsoftware.org/isdl.php 에서 설치 후 재실행하세요.
    pause
    exit /b 1
)

:: repo 루트 기준으로 경로 설정
pushd %~dp0..
set REPO_ROOT=%CD%
popd

set DIST_DIR=%~dp0dist
set BACKEND_DIR=%REPO_ROOT%\backend
set FRONTEND_DIR=%REPO_ROOT%\frontend

:: dist 디렉터리 초기화
if exist "%DIST_DIR%" rd /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"

echo.
echo [1/5] 프론트엔드 빌드 (Next.js standalone)...
cd /d "%FRONTEND_DIR%"
call npm ci --silent
call npm run build
if errorlevel 1 (echo [ERROR] 프론트엔드 빌드 실패 & pause & exit /b 1)
:: standalone 결과물 복사
xcopy ".next\standalone\*" "%DIST_DIR%\frontend\" /s /e /q /i
xcopy ".next\static\*"     "%DIST_DIR%\frontend\.next\static\" /s /e /q /i
xcopy "public\*"           "%DIST_DIR%\frontend\public\" /s /e /q /i
echo [1/5] 완료

echo.
echo [2/5] 백엔드 소스 복사...
xcopy "%BACKEND_DIR%\app\*"         "%DIST_DIR%\backend\app\"      /s /e /q /i
xcopy "%BACKEND_DIR%\alembic\*"     "%DIST_DIR%\backend\alembic\"  /s /e /q /i
copy  "%BACKEND_DIR%\alembic.ini"   "%DIST_DIR%\backend\" > nul
copy  "%BACKEND_DIR%\.env.local"    "%DIST_DIR%\.env"     > nul
echo [2/5] 완료

echo.
echo [3/5] Python 임베디드 런타임 + 패키지 준비...
:: Python embeddable zip 다운로드 (없으면 안내)
if not exist "%DIST_DIR%\python\python.exe" (
    echo [INFO] Python embeddable 패키지를 dist\python\ 에 수동으로 배치하세요.
    echo        https://www.python.org/downloads/windows/ (Embeddable Package)
    echo        pip 설치 및 패키지 설치 방법: docs\WINDOWS_PORTABLE_STRATEGY.md 참고
    pause
)
echo [3/5] 완료

echo.
echo [4/5] PyInstaller 런처 빌드...
pip install pyinstaller pystray pillow --quiet
cd /d "%~dp0launcher"
pyinstaller launcher.spec --distpath "%DIST_DIR%" --workpath "%~dp0build_tmp" --noconfirm
if errorlevel 1 (echo [ERROR] PyInstaller 빌드 실패 & pause & exit /b 1)
echo [4/5] 완료

echo.
echo [5/5] Inno Setup 인스톨러 컴파일...
cd /d "%~dp0"
%ISCC% setup.iss
if errorlevel 1 (echo [ERROR] Inno Setup 컴파일 실패 & pause & exit /b 1)
echo [5/5] 완료

echo.
echo ============================================================
echo  빌드 완료!
echo  결과물: %~dp0Output\NCVS_Setup.exe
echo ============================================================
pause
