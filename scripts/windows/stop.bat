@echo off
chcp 65001 > nul
title NCVS 종료

echo [NCVS] 서버를 종료합니다...

taskkill /FI "WINDOWTITLE eq NCVS-Backend*" /F > nul 2>&1
taskkill /FI "WINDOWTITLE eq NCVS-Frontend*" /F > nul 2>&1

echo [NCVS] 종료 완료.
timeout /t 2 /nobreak > nul
