# pytest-dsl 关键字列表功能

## 概述

pytest-dsl 现在支持列出所有可用的关键字和参数信息，帮助用户快速了解可用的功能。

## 使用方法

### 1. 使用子命令方式

```bash
# 列出所有关键字
python -m pytest_dsl.cli list-keywords

# 只显示内置关键字
python -m pytest_dsl.cli list-keywords --category builtin

# 只显示自定义关键字
python -m pytest_dsl.cli list-keywords --category custom

# 只显示远程关键字
python -m pytest_dsl.cli list-keywords --category remote

# 过滤包含特定名称的关键字
python -m pytest_dsl.cli list-keywords --filter "HTTP"

# 以JSON格式输出
python -m pytest_dsl.cli list-keywords --format json

# 组合使用
python -m pytest_dsl.cli list-keywords --category builtin --filter "断言" --format json
```

### 2. 使用向后兼容的选项方式

```bash
# 列出所有关键字
python -m pytest_dsl.cli --list-keywords

# 过滤关键字
python -m pytest_dsl.cli --list-keywords --filter "HTTP"

# JSON格式输出
python -m pytest_dsl.cli --list-keywords --format json --category builtin
```

## 输出格式

### 文本格式（默认）

```
正在加载关键字...
内置关键字模块加载完成
提示: 未在项目中找到keywords目录

找到 19 个关键字:
  内置: 19 个
------------------------------------------------------------

=== 内置关键字 ===

关键字: HTTP请求
  参数:
    客户端 (client): 客户端名称，对应YAML变量文件中的客户端配置
    配置 (config): 包含请求、捕获和断言的YAML配置
    会话 (session): 会话名称，用于在多个请求间保持会话状态
    保存响应 (save_response): 将完整响应保存到指定变量名中
    禁用授权 (disable_auth): 禁用客户端配置中的授权机制，默认为false
    模板 (template): 使用YAML变量文件中定义的请求模板
    断言重试次数 (assert_retry_count): 断言失败时的重试次数
    断言重试间隔 (assert_retry_interval): 断言重试间隔时间（秒）
  说明: 执行HTTP请求

关键字: 断言
  参数:
    条件 (condition): 条件表达式
    消息 (message): 断言失败时的错误消息
  说明: 执行条件断言
```

### JSON格式

```json
{
  "summary": {
    "total_count": 19,
    "category_counts": {
      "builtin": 19
    }
  },
  "keywords": [
    {
      "name": "HTTP请求",
      "category": "builtin",
      "parameters": [
        {
          "name": "客户端",
          "mapping": "client",
          "description": "客户端名称，对应YAML变量文件中的客户端配置"
        },
        {
          "name": "配置",
          "mapping": "config",
          "description": "包含请求、捕获和断言的YAML配置"
        }
      ],
      "documentation": "执行HTTP请求\n\n根据YAML配置发送HTTP请求，支持客户端配置、会话管理、响应捕获和断言。"
    }
  ]
}
```

## 关键字分类

- **内置关键字 (builtin)**: 由 pytest-dsl 内置提供的关键字
- **自定义关键字 (custom)**: 用户在项目的 `keywords` 目录中定义的关键字
- **远程关键字 (remote)**: 来自远程关键字服务器的关键字

## 参数说明

每个关键字都包含以下信息：

- **关键字名称**: 在DSL中使用的名称
- **参数列表**: 包含参数名、内部映射名和描述
- **说明文档**: 关键字的详细说明（如果有）
- **类别**: 关键字的来源类别

对于远程关键字，还包含：
- **远程服务器**: 关键字所在的远程服务器别名
- **原始名称**: 在远程服务器上的原始名称

## 命令行选项

| 选项 | 描述 | 可选值 |
|------|------|--------|
| `--format` | 输出格式 | `text` (默认), `json` |
| `--filter` | 过滤关键字名称 | 任意字符串（支持部分匹配） |
| `--category` | 关键字类别 | `builtin`, `custom`, `remote`, `all` (默认) |

## 实用示例

### 查看所有HTTP相关的关键字
```bash
python -m pytest_dsl.cli list-keywords --filter "HTTP"
```

### 查看所有断言关键字
```bash
python -m pytest_dsl.cli list-keywords --filter "断言"
```

### 导出所有关键字信息到JSON文件
```bash
python -m pytest_dsl.cli list-keywords --format json > keywords.json
```

### 检查自定义关键字
```bash
python -m pytest_dsl.cli list-keywords --category custom
```

这个功能对于了解可用关键字、编写DSL文件和调试自定义关键字非常有用。 