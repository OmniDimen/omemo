#!/bin/bash

# Omni Memory 启动脚本 (macOS)
# 双击此文件即可启动服务

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "🚀 Omni Memory 启动中..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    echo "请先安装 Python3: https://www.python.org/downloads/"
    echo ""
    echo "按任意键退出..."
    read -n 1
    exit 1
fi

# 检查依赖是否安装
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "📦 首次运行，正在安装依赖..."
    python3 -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        echo ""
        echo "按任意键退出..."
        read -n 1
        exit 1
    fi
    echo "✅ 依赖安装完成"
    echo ""
fi

# 创建必要的目录
mkdir -p data config

# 启动应用
echo "🌟 启动 Omni Memory..."
echo ""
echo "访问地址:"
echo "  - WebUI: http://localhost:8080"
echo "  - API:   http://localhost:8080/v1"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

python3 main.py
