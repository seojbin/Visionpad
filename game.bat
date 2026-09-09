@echo off
chcp 65001 > nul
setlocal

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo 가상환경이 없습니다.
    echo python -m venv venv 를 먼저 실행하세요.
    pause
    exit /b 1
)

call "venv\Scripts\activate.bat"

echo VisionPad Game 시작

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8003'"

python -m uvicorn game_app:app --host 127.0.0.1 --port 8003

pause
endlocal