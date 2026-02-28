#!/bin/bash

# Omni Memory 启动脚本

echo "🚀 Omni Memory 启动中..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    exit 1
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

python3 main.py
