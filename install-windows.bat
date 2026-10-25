@echo off
rem First-time setup on Windows. The installer logic is engine\launcher\setup_game.py.
rem Options are passed through, e.g. install-windows.bat --with-pad (also installs the Bluetooth pad SDK).
chcp 65001 > nul
setlocal
rem Read settings and print messages as UTF-8 regardless of the Windows code page (cp949 etc.).
set "PYTHONUTF8=1"
cd /d "%~dp0"
where py > nul 2>&1
if not errorlevel 1 (
    rem Python 3.12 is the tested version; use it when installed, otherwise the newest Python 3.
    py -3.12 -c "import sys" > nul 2>&1
    if not errorlevel 1 (
        py -3.12 engine\launcher\setup_game.py %*
    ) else (
        py -3 engine\launcher\setup_game.py %*
    )
) else (
    where python > nul 2>&1
    if errorlevel 1 (
        echo Python 3.11 이상을 먼저 설치하고 PATH에 추가한 뒤 다시 실행해 주세요.
        pause
        exit /b 1
    )
    python engine\launcher\setup_game.py %*
)
if errorlevel 1 (
    echo 준비하지 못한 항목이 있습니다. 위의 안내를 확인하고 다시 실행하세요.
    pause
    exit /b 1
)
echo 준비가 끝났습니다. start-windows.bat를 열어 주세요.
pause
endlocal
