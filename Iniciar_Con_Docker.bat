@echo off
setlocal

cd /d "%~dp0"
docker compose up -d --build --wait
if errorlevel 1 (
	exit /b 1
)

start "" "http://localhost:8000"

endlocal