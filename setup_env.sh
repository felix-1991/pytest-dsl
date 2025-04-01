#!/bin/bash
# 设置开发环境脚本

set -e

echo "===== 设置pytest-dsl开发环境 ====="
echo

# 检查是否已安装uv
if ! command -v uv &> /dev/null; then
    echo "安装uv包管理器..."
    pip install uv
fi

# 创建虚拟环境并安装开发依赖
echo "创建开发虚拟环境..."
uv venv

echo "安装开发依赖..."
uv pip install -e ".[dev]"

echo
echo "===== 环境设置完成 ====="
echo "可以使用以下命令激活环境："
echo "  . .venv/bin/activate"
echo
echo "运行测试："
echo "  pytest tests/"
echo
echo "安装开发模式："
echo "  pip install -e ."
echo 