# pytest-dsl-list 命令使用指南

`pytest-dsl-list` 是 pytest-dsl 框架提供的命令行工具，用于查看和导出可用的关键字信息。

## 命令概述

```bash
pytest-dsl-list [选项]
```

## 命令选项

### --format (输出格式)

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

### --output, -o (输出文件)

指定输出文件路径：

- JSON格式默认保存为 `keywords.json`
- HTML格式默认保存为 `keywords.html`
- 文本格式默认输出到控制台

```bash
# 保存到指定文件
pytest-dsl-list --format json --output my_keywords.json
pytest-dsl-list --format html -o docs/keywords.html
pytest-dsl-list --format text -o keywords.txt
```

### --filter (名称过滤)

根据关键字名称进行过滤（支持部分匹配）：

```bash
# 查找包含"http"的关键字
pytest-dsl-list --filter http

# 查找包含"assert"的关键字
pytest-dsl-list --filter assert --format text
```

### --category (类别过滤)

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

### --include-remote (包含远程关键字)

是否包含远程关键字（默认不包含）：

```bash
# 包含远程关键字
pytest-dsl-list --include-remote

# 只查看远程关键字
pytest-dsl-list --category remote --include-remote
```

## 使用示例

### 1. 查看所有关键字（JSON格式）

```bash
pytest-dsl-list
```

输出示例：
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
      "name": "发送HTTP请求",
      "category": "builtin",
      "description": "发送HTTP请求并返回响应",
      "parameters": [...]
    }
  ]
}
```

### 2. 查看所有关键字（文本格式）

```bash
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

关键字: 发送HTTP请求
类别: builtin
描述: 发送HTTP请求并返回响应
参数:
  - url: 请求URL (必需)
  - method: HTTP方法 (默认: GET)
  - headers: 请求头 (可选)
来源: 内置模块 http_keywords
```

### 3. 生成HTML报告

```bash
pytest-dsl-list --format html --output keywords_report.html
```

这将生成一个美观的HTML报告，包含：
- 关键字统计信息
- 按类别分组的关键字列表
- 搜索和过滤功能
- 详细的参数说明

### 4. 查找特定关键字

```bash
# 查找HTTP相关关键字
pytest-dsl-list --filter http --format text

# 查找断言相关关键字
pytest-dsl-list --filter assert --format text
```

### 5. 按类别查看关键字

```bash
# 只查看内置关键字
pytest-dsl-list --category builtin --format text

# 查看项目自定义关键字并生成HTML报告
pytest-dsl-list --category project_custom --format html -o custom_keywords.html
```

### 6. 包含远程关键字

```bash
# 查看所有关键字（包括远程）
pytest-dsl-list --include-remote --format html

# 只查看远程关键字
pytest-dsl-list --category remote --include-remote --format text
```

## 输出格式详解

### JSON格式

JSON格式包含完整的结构化数据：

```json
{
  "summary": {
    "total_count": 数量,
    "category_counts": {类别统计},
    "source_counts": {来源统计}
  },
  "keywords": [
    {
      "name": "关键字名称",
      "category": "类别",
      "description": "描述",
      "parameters": [
        {
          "name": "参数名",
          "mapping": "映射名",
          "description": "参数描述",
          "default": "默认值(可选)"
        }
      ],
      "source": "来源信息",
      "file": "文件路径"
    }
  ]
}
```

### HTML格式

HTML格式生成交互式网页报告，包含：
- 响应式设计，支持桌面和移动设备
- 实时搜索功能
- 类别筛选
- 折叠/展开详情
- 美观的样式设计

### 文本格式

文本格式提供易读的控制台输出：
- 按类别分组显示
- 清晰的层次结构
- 完整的参数信息
- 适合快速查看和调试

## 常见用法场景

### 开发时查看可用关键字

```bash
# 快速查看所有内置关键字
pytest-dsl-list --category builtin --format text
```

### 生成项目文档

```bash
# 为项目生成关键字文档
pytest-dsl-list --format html --output docs/keywords.html
```

### 调试关键字问题

```bash
# 查找特定关键字是否存在
pytest-dsl-list --filter "关键字名称" --format text

# 检查项目自定义关键字
pytest-dsl-list --category project_custom --format text
```

### 导出关键字数据

```bash
# 导出JSON数据供其他工具使用
pytest-dsl-list --format json --output keywords_export.json
```

## 注意事项

1. **项目自定义关键字**: 命令会自动扫描当前目录及子目录中的 `.resource` 文件
2. **远程关键字**: 需要使用 `--include-remote` 选项才会显示
3. **文件输出**: HTML和JSON格式默认保存文件，文本格式默认输出到控制台
4. **编码**: 输出文件使用UTF-8编码，支持中文显示

## 故障排除

### 模板文件不存在错误

如果遇到以下错误：
```
生成HTML报告失败: 'keywords_report.html' not found in search path
```

这通常是因为安装的pytest-dsl版本缺少HTML模板文件。请升级到最新版本：

```bash
pip install --upgrade pytest-dsl
```

### 关键字加载失败

如果关键字加载失败，请检查：
1. pytest-dsl是否正确安装
2. 相关插件是否安装
3. 项目配置是否正确

### 中文显示问题

确保终端支持UTF-8编码，或使用文件输出：

```bash
pytest-dsl-list --format text --output keywords.txt
``` 