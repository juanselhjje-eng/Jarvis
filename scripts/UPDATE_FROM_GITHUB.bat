@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

set "URL=https://github.com/juanselhjje-eng/Jarvis/archive/refs/heads/main.zip"
set "ZIP=%TEMP%\jarvis-main.zip"
set "TMP=%TEMP%\jarvis-main-update"
set "TARGET=%CD%"

echo [JARVIS] Descargando la version actual desde GitHub...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing '%URL%' -OutFile '%ZIP%'"
if errorlevel 1 (
    echo [ERROR] No se pudo descargar el repositorio.
    pause
    exit /b 1
)

if exist "%TMP%" rmdir /s /q "%TMP%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Force '%ZIP%' '%TMP%'"
if errorlevel 1 (
    echo [ERROR] No se pudo extraer el repositorio.
    pause
    exit /b 1
)

if not exist "%TMP%\Jarvis-main\main.py" (
    echo [ERROR] La descarga no contiene un main.py valido.
    pause
    exit /b 1
)

echo [JARVIS] Reemplazando el codigo del proyecto...
robocopy "%TMP%\Jarvis-main" "%TARGET%" /E /XD .git .venv data\necho.
echo [JARVIS] Codigo actualizado. Tu .env y tu entorno virtual local se conservan.
echo [JARVIS] Ejecuta ahora: py main.py
pause
