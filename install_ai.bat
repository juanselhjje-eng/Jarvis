@echo off
cd /d %~dp0
if not exist .venv py -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
python -m py_compile app.py core\command_router.py providers\ollama_provider.py providers\cloud_providers.py tools\system_tools.py tools\registry.py ui\main_window.py ui\voice.py
if errorlevel 1 (echo ERROR: hay un error de sintaxis.&pause&exit /b 1)
echo JARVIS MULTI-AI instalado correctamente.
echo Edita .env para poner tus API keys.
pause
