@echo off
chcp 65001 >nul
title Geocode Web - Frontend

cd /d "%~dp0"

python -c "import urllib.request; urllib.request.urlopen('http://localhost:35696/api/health',timeout=2)" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Starting backend in background...
    wscript //nologo "%~dp0..\run_backend.vbs"
    timeout /t 4 /nobreak >nul
)

if not exist node_modules (
    echo [INFO] Installing frontend dependencies...
    npm install >nul 2>&1
)

npm run dev
pause
