# 命令行工具使用示例

本示例展示如何使用pytest-dsl提供的各种命令行工具来提高开发效率和项目管理。

## 学习目标

通过这个示例，您将学会：

- 使用 `pytest-dsl-list` 查看和管理关键字
- 生成项目文档和关键字报告
- 集成命令行工具到开发工作流
- 在自动化流程中使用命令行工具

## 示例项目结构

```
cli-tools-example/
├── tests/
│   ├── api/
│   │   ├── user_api.dsl
│   │   └── auth_api.dsl
│   └── ui/
│       └── login_ui.dsl
├── resources/
│   ├── api_utils.resource
│   └── ui_utils.resource
├── config/
│   └── test_config.yaml
├── scripts/
│   ├── generate_docs.sh
│   ├── check_keywords.sh
│   └── ci_build.sh
├── docs/
│   └── generated/
└── README.md
```

## 基础用法示例

### 1. 查看所有可用关键字

```bash
# 快速查看所有关键字
pytest-dsl-list --format text
```

输出示例：
```
找到 52 个关键字:
  内置: 25 个
  插件: 15 个
  项目自定义: 12 个
------------------------------------------------------------

=== 内置关键字 ===

关键字: HTTP请求
类别: builtin
描述: 发送HTTP请求并返回响应
参数:
  - 客户端: HTTP客户端名称 (默认: default)
  - 配置: 请求配置 (必需)
  - 步骤名称: 步骤描述 (可选)
来源: 内置模块 http_keywords

关键字: 断言
类别: builtin
描述: 执行断言验证
参数:
  - 条件: 断言条件表达式 (必需)
  - 消息: 失败时的错误消息 (可选)
来源: 内置模块 assertion_keywords
```

### 2. 查找特定功能的关键字

```bash
# 查找HTTP相关关键字
pytest-dsl-list --filter http --format text

# 查找断言相关关键字
pytest-dsl-list --filter assert --format text

# 查找数据库相关关键字
pytest-dsl-list --filter 数据库 --format text
```

### 3. 按类别查看关键字

```bash
# 只查看内置关键字
pytest-dsl-list --category builtin --format text

# 查看项目自定义关键字
pytest-dsl-list --category project_custom --format text

# 查看所有关键字（包括远程）
pytest-dsl-list --include-remote --format text
```

## 文档生成示例

### 生成HTML关键字文档

创建脚本 `scripts/generate_docs.sh`：

```bash
#!/bin/bash

echo "=== 生成pytest-dsl项目文档 ==="

# 创建文档目录
mkdir -p docs/generated

# 生成完整的关键字文档
echo "1. 生成完整关键字文档..."
pytest-dsl-list --format html --output docs/generated/all_keywords.html

# 生成内置关键字文档
echo "2. 生成内置关键字文档..."
pytest-dsl-list --category builtin --format html --output docs/generated/builtin_keywords.html

# 生成项目自定义关键字文档
echo "3. 生成项目自定义关键字文档..."
pytest-dsl-list --category project_custom --format html --output docs/generated/custom_keywords.html

# 生成JSON数据供其他工具使用
echo "4. 导出关键字数据..."
pytest-dsl-list --format json --output docs/generated/keywords.json

# 生成关键字统计报告
echo "5. 生成统计报告..."
pytest-dsl-list --format json --output docs/generated/keywords.json
jq '.summary' docs/generated/keywords.json > docs/generated/keywords_summary.json

echo "文档生成完成！"
echo "查看生成的文档："
echo "  - 完整文档: docs/generated/all_keywords.html"
echo "  - 内置关键字: docs/generated/builtin_keywords.html"
echo "  - 自定义关键字: docs/generated/custom_keywords.html"
echo "  - JSON数据: docs/generated/keywords.json"
```

运行脚本：

```bash
chmod +x scripts/generate_docs.sh
./scripts/generate_docs.sh
```

### 生成的HTML文档特性

生成的HTML文档包含以下特性：

- **📊 统计信息** - 关键字数量和分类统计
- **🔍 实时搜索** - 支持关键字名称和描述搜索
- **📂 分类筛选** - 按类别筛选关键字
- **📋 详细信息** - 完整的参数说明和示例
- **📱 响应式设计** - 支持桌面和移动设备
- **🎨 美观界面** - 现代化的UI设计

## 开发工作流集成

### 关键字检查脚本

创建脚本 `scripts/check_keywords.sh`：

```bash
#!/bin/bash

echo "=== 检查项目关键字状态 ==="

# 检查关键字总数
echo "1. 关键字统计："
pytest-dsl-list --format json --output keywords.json
jq '.summary' keywords.json

echo ""
echo "2. 内置关键字列表："
pytest-dsl-list --category builtin --format text | head -20

echo ""
echo "3. 项目自定义关键字："
pytest-dsl-list --category project_custom --format json --output custom_keywords.json
custom_count=$(jq '.summary.total_count' custom_keywords.json)
if [ "$custom_count" -gt 0 ]; then
    echo "找到 $custom_count 个自定义关键字："
    pytest-dsl-list --category project_custom --format text
else
    echo "未找到项目自定义关键字"
fi

echo ""
echo "4. 查找常用关键字："
echo "HTTP相关关键字："
pytest-dsl-list --filter http --format text | grep "关键字:" | head -5

echo ""
echo "断言相关关键字："
pytest-dsl-list --filter assert --format text | grep "关键字:" | head -5

echo ""
echo "=== 检查完成 ==="
```

### 项目验证脚本

创建脚本 `scripts/validate_project.sh`：

```bash
#!/bin/bash

echo "=== 验证项目配置 ==="

# 检查pytest-dsl安装
echo "1. 检查pytest-dsl安装状态："
if command -v pytest-dsl-list &> /dev/null; then
    echo "✅ pytest-dsl已安装"
    pip show pytest-dsl | grep Version
else
    echo "❌ pytest-dsl未安装"
    exit 1
fi

# 检查关键字加载
echo ""
echo "2. 检查关键字加载："
pytest-dsl-list --format json --output keywords.json
total_keywords=$(jq '.summary.total_count' keywords.json)
if [ "$total_keywords" -gt 0 ]; then
    echo "✅ 成功加载 $total_keywords 个关键字"
else
    echo "❌ 关键字加载失败"
    exit 1
fi

# 检查项目自定义关键字
echo ""
echo "3. 检查项目自定义关键字："
pytest-dsl-list --category project_custom --format json --output custom_keywords.json
custom_keywords=$(jq '.summary.total_count' custom_keywords.json)
echo "📋 找到 $custom_keywords 个项目自定义关键字"

# 检查资源文件
echo ""
echo "4. 检查资源文件："
if find . -name "*.resource" -type f | head -1 > /dev/null; then
    resource_count=$(find . -name "*.resource" -type f | wc -l)
    echo "✅ 找到 $resource_count 个资源文件"
    find . -name "*.resource" -type f | head -5
else
    echo "⚠️  未找到资源文件"
fi

# 检查测试文件
echo ""
echo "5. 检查测试文件："
if find . -name "*.dsl" -type f | head -1 > /dev/null; then
    dsl_count=$(find . -name "*.dsl" -type f | wc -l)
    echo "✅ 找到 $dsl_count 个DSL测试文件"
    find . -name "*.dsl" -type f | head -5
else
    echo "⚠️  未找到DSL测试文件"
fi

echo ""
echo "=== 验证完成 ==="
```

## 自动化示例

### GitHub Actions工作流

创建 `.github/workflows/docs.yml`：

```yaml
name: Generate Documentation

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  generate-docs:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install pytest-dsl
        pip install jq
    
    - name: Validate project
      run: |
        chmod +x scripts/validate_project.sh
        ./scripts/validate_project.sh
    
    - name: Generate documentation
      run: |
        chmod +x scripts/generate_docs.sh
        ./scripts/generate_docs.sh
    
    - name: Upload documentation artifacts
      uses: actions/upload-artifact@v3
      with:
        name: documentation
        path: docs/generated/
    
    - name: Deploy to GitHub Pages
      if: github.ref == 'refs/heads/main'
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./docs/generated
        destination_dir: keywords
```

## 相关资源

- **[命令行工具指南](../guide/cli-tools)** - 详细的命令行工具文档
- **[最佳实践](../guide/best-practices)** - 项目组织和开发规范 
