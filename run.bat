@echo off
chcp 65001 > nul
setlocal

cd /d "%~dp0"

echo ==================================================
echo VideoBraille
echo ==================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [오류] venv가 존재하지 않습니다.
    pause
    exit /b 1
)

call "venv\Scripts\activate.bat"

echo Python:
python --version

echo.
echo ==================================================
echo VideoBraille 메인 프로그램 시작
echo ==================================================
echo.

python main.py

echo.
echo ==================================================
echo VideoBraille 작업 종료
echo ==================================================
echo.

pause
endlocal