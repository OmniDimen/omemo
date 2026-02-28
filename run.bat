@echo off
chcp 65001 >nul

:: Omni Memory 启动脚本 (Windows)

echo 🚀 Omni Memory 启动中...

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    exit /b 1
)

:: 创建必要的目录
if not exist "data" mkdir data
if not exist "config" mkdir config

:: 启动应用
echo 🌟 启动 Omni Memory...
echo.
echo 访问地址:
echo   - WebUI: http://localhost:8080
echo   - API:   http://localhost:8080/v1
echo.

python main.py
