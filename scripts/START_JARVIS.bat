@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No existe el entorno virtual .venv
    echo Crea uno con: python -m venv .venv
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python main.py
if errorlevel 1 pause
