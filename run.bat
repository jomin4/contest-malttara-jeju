@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
where py >nul 2>nul && (py -3 run.py %* & goto :end)
where python >nul 2>nul && (python run.py %* & goto :end)
echo Python 3.11 이상이 필요합니다. https://www.python.org/downloads/ 에서 설치한 뒤 다시 실행해 주세요.
:end
pause
