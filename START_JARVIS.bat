@echo off
setlocal
cd /d C:\JARVIS
if not exist .venv\Scripts\activate.bat (
  echo No existe C:\JARVIS\.venv
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python app.py
if errorlevel 1 pause
