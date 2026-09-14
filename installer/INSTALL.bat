@echo off
title 거북선 작업대 설치
echo.
echo   ========================================
echo    거북선 컷 작업대 - 바탕화면 설치
echo   ========================================
echo.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
  echo.
  echo   설치하지 못했습니다. 위 메시지를 확인해 주세요.
) 
echo.
pause
