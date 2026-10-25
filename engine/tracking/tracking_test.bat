@echo off
setlocal
rem Lives in engine\tracking\; runs from the repository root, so the venv lookup below is unchanged.
cd /d "%~dp0..\.."

set "PYTHON_EXE="

if exist "venv\Scripts\python.exe" set "PYTHON_EXE=venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "..\venv\Scripts\python.exe" set "PYTHON_EXE=..\venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "..\.venv\Scripts\python.exe" set "PYTHON_EXE=..\.venv\Scripts\python.exe"

if not defined PYTHON_EXE (
    echo Virtual environment not found.
    echo Create it with: python -m venv venv
    pause
    exit /b 1
)

echo Using: %PYTHON_EXE%
"%PYTHON_EXE%" engine\tracking\tracking_test.py

if errorlevel 1 (
    echo.
    echo tracking_test.py exited with an error.
)

pause
endlocal
