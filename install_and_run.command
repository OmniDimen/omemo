#!/bin/bash

# ============================================
# Omni Memory 一键安装启动脚本 (macOS)
# 双击此文件即可自动下载、安装并启动
# ============================================

echo ""
echo "🧠 Omni Memory 一键安装启动"
echo "=========================="
echo ""

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3"
    echo ""
    echo "请先安装 Python3："
    echo "  方法一：访问 https://www.python.org/downloads/ 下载安装"
    echo "  方法二：终端运行 brew install python3（需要先装 Homebrew）"
    echo ""
    echo "安装完成后重新双击此文件即可"
    echo ""
    read -p "按回车键退出..."
    exit 1
fi

echo "✅ Python3 已就绪：$(python3 --version)"

# 检查 git
if ! command -v git &> /dev/null; then
    echo "❌ 未找到 Git"
    echo ""
    echo "请先安装 Git："
    echo "  在终端运行：xcode-select --install"
    echo ""
    read -p "按回车键退出..."
    exit 1
fi

echo "✅ Git 已就绪"

# 设定安装目录（脚本所在目录下的 omemo 文件夹）
INSTALL_DIR="$(dirname "$0")/omemo"

# 如果已经安装过，直接启动
if [ -d "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/main.py" ]; then
    echo ""
    echo "📂 检测到已安装，直接启动..."
    cd "$INSTALL_DIR"
    
    # 检查依赖
    if ! python3 -c "import fastapi" &> /dev/null; then
        echo "📦 安装依赖..."
        python3 -m pip install -r requirements.txt
    fi
    
    echo ""
    echo "🌟 启动 Omni Memory..."
    echo ""
    echo "访问地址："
    echo "  - WebUI: http://localhost:8080"
    echo "  - API:   http://localhost:8080/v1"
    echo ""
    echo "按 Ctrl+C 停止服务"
    echo ""
    python3 main.py
    exit 0
fi

# 首次安装
echo ""
echo "📥 正在下载 Omni Memory..."
git clone https://github.com/OmniDimen/omemo.git "$INSTALL_DIR"

if [ $? -ne 0 ]; then
    echo "❌ 下载失败，请检查网络连接"
    echo ""
    read -p "按回车键退出..."
    exit 1
fi

echo "✅ 下载完成"

# 安装依赖
cd "$INSTALL_DIR"
echo ""
echo "📦 正在安装依赖..."
python3 -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  依赖安装失败，尝试使用备选方式..."
    python3 -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
fi

echo ""
echo "✅ 安装完成！"

# 创建必要目录
mkdir -p data config

# 启动
echo ""
echo "🌟 启动 Omni Memory..."
echo ""
echo "访问地址："
echo "  - WebUI: http://localhost:8080"
echo "  - API:   http://localhost:8080/v1"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

python3 main.py
