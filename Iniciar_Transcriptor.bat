@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
)

".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install flask yt-dlp youtube-transcript-api >nul
start "" ".venv\Scripts\python.exe" "app.py"

endlocal