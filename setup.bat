```bat
@echo off
chcp 65001 > nul
setlocal

cd /d "%~dp0"

echo ==================================================
echo Setup
echo ==================================================
echo.

REM --------------------------------------------------
REM 1. Python 확인
REM --------------------------------------------------

echo [1/8] Python 확인
python --version > nul 2>&1

if errorlevel 1 (
    echo.
    echo [오류] Python을 찾을 수 없습니다.
    echo Python 3.11 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

python --version


REM --------------------------------------------------
REM 2. venv 생성
REM --------------------------------------------------

echo.
echo [2/8] 가상환경 확인

if not exist "venv\Scripts\python.exe" (

    echo venv가 없습니다.
    echo 새 가상환경을 생성합니다...

    python -m venv venv

    if errorlevel 1 (
        echo.
        echo [오류] venv 생성 실패
        pause
        exit /b 1
    )

) else (

    echo 기존 venv를 사용합니다.

)


REM --------------------------------------------------
REM 3. venv 활성화
REM --------------------------------------------------

call "venv\Scripts\activate.bat"

if errorlevel 1 (
    echo.
    echo [오류] venv 활성화 실패
    pause
    exit /b 1
)


REM --------------------------------------------------
REM 4. pip 업데이트
REM --------------------------------------------------

echo.
echo [3/8] pip 업데이트

python -m pip install --upgrade pip setuptools wheel

if errorlevel 1 (
    echo.
    echo [오류] pip 업데이트 실패
    pause
    exit /b 1
)


REM --------------------------------------------------
REM 5. 일반 requirements 설치
REM --------------------------------------------------

echo.
echo [4/8] requirements.txt 설치

if not exist "requirements.txt" (
    echo.
    echo [오류] requirements.txt 파일이 없습니다.
    pause
    exit /b 1
)

pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [오류] requirements.txt 설치 실패
    pause
    exit /b 1
)


REM --------------------------------------------------
REM 6. PyTorch CUDA 12.1
REM --------------------------------------------------

echo.
echo [5/8] PyTorch CUDA 12.1 설치

pip install ^
    torch==2.5.1 ^
    torchvision==0.20.1 ^
    torchaudio==2.5.1 ^
    --index-url https://download.pytorch.org/whl/cu121

if errorlevel 1 (
    echo.
    echo [오류] PyTorch CUDA 설치 실패
    pause
    exit /b 1
)


REM --------------------------------------------------
REM 7. rembg GPU
REM --------------------------------------------------

echo.
echo [6/8] rembg GPU 지원 설치

pip install --upgrade "rembg[gpu]"

if errorlevel 1 (
    echo.
    echo [오류] rembg GPU 설치 실패
    pause
    exit /b 1
)


REM --------------------------------------------------
REM 8. llama-cpp-python CUDA
REM --------------------------------------------------

echo.
echo [7/8] llama-cpp-python CUDA 설치

REM CPU 버전이 먼저 설치되어 있을 가능성이 있으므로 제거
pip uninstall llama-cpp-python -y > nul 2>&1

pip install llama-cpp-python ^
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121 ^
    --only-binary llama-cpp-python

if errorlevel 1 (
    echo.
    echo [오류] llama-cpp-python CUDA 설치 실패
    echo.
    echo CUDA 12.1용 wheel이 현재 Python 버전에
    echo 제공되지 않을 가능성이 있습니다.
    pause
    exit /b 1
)


REM --------------------------------------------------
REM 설치 확인
REM --------------------------------------------------

echo.
echo [8/8] 설치 확인
echo ==================================================

python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA runtime:', torch.version.cuda); print('CUDA available:', torch.cuda.is_available())"

echo.

python -c "import cv2; print('OpenCV:', cv2.__version__)"

echo.

python -c "import ultralytics; print('Ultralytics:', ultralytics.__version__)"

echo.

python -c "import rembg; print('rembg: OK')"

echo.

python -c "import transformers; print('Transformers:', transformers.__version__)"

echo.

python -c "import llama_cpp; print('llama-cpp-python:', llama_cpp.__version__)"

echo.

python -c "import fastapi; print('FastAPI:', fastapi.__version__)"

echo.
echo ==================================================
echo 환경 설치 완료
echo ==================================================
echo.

echo 다음 항목은 별도로 준비해야 합니다:
echo.
echo 1. FFmpeg 설치 및 PATH 등록
echo 2. models 폴더에 Gemma GGUF 모델 배치
echo 3. NVIDIA GPU Driver 설치
echo 4. Moondream3 소스코드 수정필요
echo .cache\huggingface\modules\transformers_modules\moondream\moondream3_hyphen_preview\5112966d1a723413b1c9a1e8bea272b72e647b35\moondream.py
echo mask.seq_lengths = (1, mask.seq_lengths[1])를
echo if hasattr(mask, 'seq_lengths'):
echo    mask.seq_lengths = (1, mask.seq_lengths[1])로.
echo.
echo 실행:
echo run.bat
echo.

pause
endlocal
```
