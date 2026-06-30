@echo off
setlocal

cd /d "%~dp0"

echo ============================================
echo   Transcriptor de Playlists de YouTube
echo   Modo: Docker (interfaz web)
echo ============================================
echo.

:: ── Check Docker is installed ──
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker no esta instalado.
    echo.
    echo Descarga Docker Desktop desde: https://www.docker.com/products/docker-desktop/
    echo Reinicia tu PC despues de instalarlo.
    echo.
    pause
    exit /b 1
)

:: ── Check Docker is running ──
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker no esta corriendo.
    echo.
    echo Abre Docker Desktop y espera a que inicie completamente.
    echo Luego vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

:: ── Create output folder ──
if not exist "transcripciones" mkdir transcripciones

:: ── Build and start container ──
echo [1/2] Construyendo e iniciando contenedor...
echo       (esto puede tardar la primera vez)
echo.
docker compose -f docker\docker-compose.yml up -d --build --wait
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo iniciar el contenedor.
    echo Revisa los logs con: docker compose -f docker\docker-compose.yml logs
    pause
    exit /b 1
)

:: ── Open browser ──
echo [2/2] Abriendo navegador...
echo.
echo   Interfaz web en: http://localhost:8000
echo.
echo   Para detener: docker compose -f docker\docker-compose.yml down
echo.

start "" "http://localhost:8000"

pause
endlocal