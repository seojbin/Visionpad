@echo off
chcp 65001 > nul

cd /d "%~dp0"

echo ==================================================
echo VideoBraille AI Relay Server
echo ==================================================
echo.

call "%~dp0venv\Scripts\activate.bat"

set PYTHONIOENCODING=utf-8

echo AI 서버 시작...
echo.

python -m uvicorn server:app --host 127.0.0.1 --port 8001

echo.
echo AI 서버가 종료되었습니다.
pause