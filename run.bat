@echo off
cd /d "%~dp0"

REM 尝试激活虚拟环境 (兼容 .venv 和 venv)
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment (.venv)...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment (venv)...
    call "venv\Scripts\activate.bat"
) else (
    echo No virtual environment found. Using system Python...
)

echo Starting system...
python main.py

if %errorlevel% neq 0 (
    echo.
    echo System crashed with error code %errorlevel%
    pause
)
pause