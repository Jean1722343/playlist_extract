@echo off
setlocal

cd /d "%~dp0"

echo ============================================
echo   Transcriptor de Playlists de YouTube
echo   Modo: Programa de escritorio
echo ============================================
echo.

:: ── Check Python is installed ──
where py >nul 2>&1
if errorlevel 1 (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python no esta instalado.
        echo.
        echo Descarga Python 3.10+ desde: https://www.python.org/downloads/
        echo Asegurate de marcar "Add Python to PATH" durante la instalacion.
        echo.
        pause
        exit /b 1
    )
)

:: ── Create virtual environment if needed ──
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo       Entorno virtual creado.
) else (
    echo [1/3] Entorno virtual encontrado.
)

:: ── Install dependencies ──
echo [2/3] Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
".venv\Scripts\python.exe" -m pip install yt-dlp youtube-transcript-api >nul 2>&1
echo       Dependencias listas.

:: ── Create output folder ──
if not exist "transcripciones" mkdir transcripciones

:: ── Launch desktop app ──
echo [3/3] Abriendo programa...
echo.
".venv\Scripts\python.exe" "src\app.py"

endlocal