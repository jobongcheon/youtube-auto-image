@echo off
rem 보고서 자동 작성기 - 이 아이콘 위에 파일을 끌어다 놓으면 된다
rem   .txt           -> 표준 서식 보고서(.docx)
rem   .xlsx / .xlsm  -> 분기 상담 실적 현황 보고서(.docx + 고칠 수 있는 .txt 초안)
setlocal
cd /d "%~dp0.."

set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% --version >nul 2>nul || (
  echo 파이썬이 없습니다. https://www.python.org 에서 설치할 때
  echo "Add python.exe to PATH" 를 꼭 체크하세요.
  pause & exit /b 1
)

if "%~1"=="" (
  echo 초안^(.txt^)이나 엑셀 파일을 이 아이콘 위에 끌어다 놓으세요.
  pause & exit /b 0
)

%PY% -c "import docx, openpyxl" >nul 2>nul || (
  echo 처음 한 번만 필요한 부품을 설치합니다...
  %PY% -m pip install -q -r report_auto\requirements.txt
)

if /i "%~x1"==".txt" (
  %PY% -m report_auto write "%~1"
) else (
  %PY% -m report_auto excel "%~1"
)
echo.
pause
