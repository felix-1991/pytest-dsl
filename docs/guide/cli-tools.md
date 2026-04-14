# 命令行工具

pytest-dsl提供了一系列强大的命令行工具，帮助您更高效地管理和使用DSL测试文件。

## pytest-dsl-list - 关键字查看工具

`pytest-dsl-list` 是用于查看和导出可用关键字信息的命令行工具，支持多种输出格式和过滤选项。

### 基本用法

```bash
pytest-dsl-list [选项]
```

### 命令选项

#### --format (输出格式)

指定输出格式，支持三种格式：

- `json` (默认): JSON格式输出，适合程序处理
- `text`: 文本格式输出，适合人工阅读  
- `html`: HTML格式输出，生成美观的网页报告

```bash
# JSON格式（默认）
pytest-dsl-list --format json

# 文本格式
pytest-dsl-list --format text

# HTML格式
pytest-dsl-list --format html
```

#### --output, -o (输出文件)

指定输出文件路径：

```bash
# 保存到指定文件
pytest-dsl-list --format json --output my_keywords.json
pytest-dsl-list --format html -o docs/keywords.html
pytest-dsl-list --format text -o keywords.txt
```

#### --filter (名称过滤)

根据关键字名称进行过滤（支持部分匹配）：

```bash
# 查找包含"http"的关键字
pytest-dsl-list --filter http

# 查找包含"assert"的关键字
pytest-dsl-list --filter assert --format text
```

#### --category (类别过滤)

按关键字类别进行过滤：

- `builtin`: 内置关键字
- `plugin`: 插件关键字
- `custom`: 自定义关键字
- `project_custom`: 项目自定义关键字
- `remote`: 远程关键字
- `all`: 全部关键字（默认）

```bash
# 只查看内置关键字
pytest-dsl-list --category builtin

# 只查看插件关键字
pytest-dsl-list --category plugin --format text

# 只查看项目自定义关键字
pytest-dsl-list --category project_custom --format html
```

#### --include-remote (包含远程关键字)

是否包含远程关键字（默认不包含）：

```bash
# 包含远程关键字
pytest-dsl-list --include-remote

# 只查看远程关键字
pytest-dsl-list --category remote --include-remote
```

### 实用示例

#### 1. 快速查看所有关键字

```bash
# 文本格式查看（适合快速浏览）
pytest-dsl-list --format text
```

输出示例：
```
找到 45 个关键字:
  内置: 20 个
  插件: 15 个
  自定义: 10 个
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

#### 2. 生成项目文档

```bash
# 生成HTML格式的关键字文档
pytest-dsl-list --format html --output docs/keywords.html
```

生成的HTML报告包含：
- 📊 关键字统计信息
- 🔍 实时搜索功能
- 📂 按类别分组显示
- 📋 详细的参数说明
- 📱 响应式设计

#### 3. 查找特定功能

```bash
# 查找HTTP相关关键字
pytest-dsl-list --filter http --format text

# 查找断言相关关键字
pytest-dsl-list --filter assert --format text

# 查找数据库相关关键字
pytest-dsl-list --filter 数据库 --format text
```

#### 4. 导出结构化数据

```bash
# 导出JSON数据供其他工具使用
pytest-dsl-list --format json --output keywords_export.json
```

JSON输出格式：
```json
{
  "summary": {
    "total_count": 45,
    "category_counts": {
      "builtin": 20,
      "plugin": 15,
      "custom": 10
    }
  },
  "keywords": [
    {
      "name": "HTTP请求",
      "category": "builtin",
      "description": "发送HTTP请求并返回响应",
      "parameters": [
        {
          "name": "客户端",
          "mapping": "client",
          "description": "HTTP客户端名称",
          "default": "default"
        },
        {
          "name": "配置",
          "mapping": "config",
          "description": "请求配置",
          "required": true
        }
      ],
      "source": "内置模块 http_keywords"
    }
  ]
}
```

#### 5. 检查项目自定义关键字

```bash
# 查看项目中定义的自定义关键字
pytest-dsl-list --category project_custom --format text

# 生成自定义关键字文档
pytest-dsl-list --category project_custom --format html -o custom_keywords.html
```

### 输出格式对比

| 格式 | 适用场景 | 特点 |
|------|----------|------|
| **text** | 快速查看、调试 | 易读、控制台友好 |
| **json** | 程序处理、集成 | 结构化、完整数据 |
| **html** | 文档生成、分享 | 美观、交互式 |

### 常见使用场景

#### 开发时查看可用关键字

```bash
# 快速查看所有内置关键字
pytest-dsl-list --category builtin --format text

# 查看特定功能的关键字
pytest-dsl-list --filter "HTTP" --format text
```

#### 生成项目文档

```bash
# 为项目生成完整的关键字文档
pytest-dsl-list --format html --output docs/keywords.html

# 只生成自定义关键字文档
pytest-dsl-list --category project_custom --format html --output docs/custom_keywords.html
```

#### 调试关键字问题

```bash
# 查找特定关键字是否存在
pytest-dsl-list --filter "关键字名称" --format text

# 导出 JSON 再检查所有可用的关键字类别
pytest-dsl-list --format json --output keywords.json
jq '.summary.category_counts' keywords.json
```

#### 自动化环境生成工件

```bash
# 在流水线中生成关键字文档
pytest-dsl-list --format html --output artifacts/keywords.html

# 导出关键字数据供其他工具使用
pytest-dsl-list --format json --output keywords.json
```

### 故障排除

#### 模板文件不存在错误

如果遇到以下错误：
```
生成HTML报告失败: 'keywords_report.html' not found in search path
```

解决方法：
```bash
# 升级到最新版本
pip install --upgrade pytest-dsl

# 或重新安装
pip uninstall pytest-dsl
pip install pytest-dsl
```

#### 关键字加载失败

如果关键字加载失败，请检查：

1. **pytest-dsl安装** - 确认正确安装
2. **插件依赖** - 检查相关插件是否安装
3. **项目配置** - 验证项目配置文件
4. **Python路径** - 确认Python模块路径正确

```bash
# 检查安装状态
pip show pytest-dsl

# 检查可用关键字
pytest-dsl-list --format text
```

#### 中文显示问题

确保终端支持UTF-8编码：

```bash
# 使用文件输出避免编码问题
pytest-dsl-list --format text --output keywords.txt

# 或使用HTML格式
pytest-dsl-list --format html --output keywords.html
```

## pytest-dsl-server - 远程服务器

用于启动远程关键字服务器，支持分布式测试执行。

### 基本用法

```bash
pytest-dsl-server [选项]
```

### 常用选项

```bash
# 启动服务器
pytest-dsl-server --host 0.0.0.0 --port 8270

# 带API密钥启动
pytest-dsl-server --host 0.0.0.0 --port 8270 --api-key your_secret_key

# 设置最大并发请求数
pytest-dsl-server --host 0.0.0.0 --port 8270 --max-concurrency 50

# 加载扩展
pytest-dsl-server --extensions extensions/

# 加载多个扩展
pytest-dsl-server --extensions "ext1.py,ext2.py,extensions/"
```

详细使用方法请参考 [远程关键字指南](./remote-keywords)。

## pytest-dsl - 主执行命令

用于执行DSL测试文件。

### 基本用法

```bash
# 执行单个文件
pytest-dsl test.dsl

# 执行目录下所有DSL文件
pytest-dsl tests/

# 使用配置文件
pytest-dsl tests/ --yaml-vars config/dev.yaml
```

详细使用方法请参考 [快速开始指南](./getting-started)。

## 最佳实践

### 1. 文档生成工作流

```bash
#!/bin/bash
# generate_docs.sh

echo "生成关键字文档..."

# 生成HTML文档
pytest-dsl-list --format html --output docs/keywords.html

# 生成JSON数据
pytest-dsl-list --format json --output docs/keywords.json

# 只生成自定义关键字文档
pytest-dsl-list --category project_custom --format html --output docs/custom_keywords.html

echo "文档生成完成！"
```

### 2. 开发调试脚本

```bash
#!/bin/bash
# debug_keywords.sh

echo "=== 检查关键字状态 ==="

echo "1. 所有关键字统计："
pytest-dsl-list --format json --output keywords.json
jq '.summary' keywords.json

echo "2. 内置关键字："
pytest-dsl-list --category builtin --format text | head -20

echo "3. 项目自定义关键字："
pytest-dsl-list --category project_custom --format text

echo "4. 查找HTTP相关关键字："
pytest-dsl-list --filter http --format text
```

### 3. 自动化运行

在自动化流程或流水线中运行 pytest-dsl：

```bash
# 运行所有测试
pytest-dsl tests/

# 指定配置文件
pytest-dsl tests/ --yaml-vars config/dev.yaml

# 生成关键字文档
pytest-dsl-list --format html --output artifacts/keywords.html
```

## 下一步

现在您已经掌握了pytest-dsl的命令行工具，可以继续学习：

- **[配置管理](./configuration)** - 环境配置和变量管理
- **[最佳实践](./best-practices)** - 项目组织和开发规范 
