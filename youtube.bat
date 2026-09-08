@echo off
chcp 65001 > nul
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo venv를 찾을 수 없습니다.
    pause
    exit /b 1
)

call "venv\Scripts\activate.bat"

echo YouTube Viewer 시작

python -m uvicorn youtube_app:app --host 127.0.0.1 --port 8002

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; Start-Process 'http://127.0.0.1:8002'"

pause