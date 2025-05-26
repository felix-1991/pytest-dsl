#!/bin/bash

# 远程关键字示例运行脚本
# 此脚本用于验证所有远程关键字示例

echo "=== 远程关键字示例验证脚本 ==="
echo "此脚本将验证所有远程关键字示例文件"

# 检查pytest-dsl是否安装
if ! command -v pytest-dsl &> /dev/null; then
    echo "错误: pytest-dsl 未安装或不在PATH中"
    exit 1
fi

# 检查Python模块是否可用
if ! python -c "import pytest_dsl.remote.keyword_server" 2>/dev/null; then
    echo "错误: pytest-dsl.remote.keyword_server 模块不可用"
    exit 1
fi

echo "✅ pytest-dsl 环境检查通过"

# 示例文件列表
examples=(
    "basic_remote_test.dsl"
    "http_remote_test.dsl"
    "capture_variables_test.dsl"
    "session_management_test.dsl"
    "global_variables_test.dsl"
    "comprehensive_test.dsl"
)

# 检查示例文件是否存在
echo "检查示例文件..."
for example in "${examples[@]}"; do
    if [ ! -f "$example" ]; then
        echo "❌ 示例文件不存在: $example"
        exit 1
    else
        echo "✅ 找到示例文件: $example"
    fi
done

echo ""
echo "=== 开始验证示例 ==="
echo "注意: 需要先启动远程关键字服务器"
echo "在另一个终端中运行: python -m pytest_dsl.remote.keyword_server --host localhost --port 8270"
echo ""

# 等待用户确认
read -p "请确认远程服务器已启动，按回车键继续..."

# 测试服务器连接
echo "测试服务器连接..."
if curl -s -X POST http://localhost:8270/ \
   -H "Content-Type: application/json" \
   -d '{"action": "list_keywords"}' > /dev/null; then
    echo "✅ 远程服务器连接成功"
else
    echo "❌ 无法连接到远程服务器 (localhost:8270)"
    echo "请确保远程服务器已启动"
    exit 1
fi

echo ""

# 运行示例测试
success_count=0
total_count=${#examples[@]}

for example in "${examples[@]}"; do
    echo "--- 运行示例: $example ---"
    
    if pytest-dsl "$example"; then
        echo "✅ $example 运行成功"
        ((success_count++))
    else
        echo "❌ $example 运行失败"
    fi
    
    echo ""
done

# 输出结果统计
echo "=== 验证结果统计 ==="
echo "总示例数: $total_count"
echo "成功数: $success_count"
echo "失败数: $((total_count - success_count))"

if [ $success_count -eq $total_count ]; then
    echo "🎉 所有示例验证通过！"
    exit 0
else
    echo "⚠️  部分示例验证失败"
    exit 1
fi
