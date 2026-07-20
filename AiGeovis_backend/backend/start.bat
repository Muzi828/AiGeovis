@echo off
chcp 65001 >nul
title AiGeovis 后端
echo ============================================
echo   AiGeovis API 后端启动
echo   地址: http://localhost:35696
echo   文档: http://localhost:35696/docs
echo ============================================
echo.

cd /d "%~dp0"

python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo [INFO] 正在安装后端依赖，请稍候...
    pip install -r requirements.txt
    echo.
)

echo [INFO] 启动中...按 Ctrl+C 停止
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

pause
