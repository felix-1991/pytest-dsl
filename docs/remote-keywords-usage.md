# 远程关键字使用指南

本文档介绍如何使用pytest-dsl的远程关键字功能，包括服务器启动、客户端连接和DSL语法。

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [服务器配置](#服务器配置)
- [客户端使用](#客户端使用)
- [DSL语法](#dsl语法)
- [高级功能](#高级功能)
- [故障排除](#故障排除)

## 概述

远程关键字功能允许你在分布式环境中执行测试，支持：

- 跨网络执行关键字
- 变量捕获和传递
- 会话状态管理
- 全局变量同步
- HTTP请求代理

## 快速开始

### 1. 启动远程关键字服务器

```bash
# 基本启动
python -m pytest_dsl.remote.keyword_server

# 指定地址和端口
python -m pytest_dsl.remote.keyword_server --host 0.0.0.0 --port 8270

# 启用API密钥认证
python -m pytest_dsl.remote.keyword_server --api-key your_secret_key
```

### 2. 创建DSL测试文件

```dsl
@name: "远程关键字示例"
@remote: "http://localhost:8270/" as remote_server

# 远程执行打印
remote_server|[打印],内容: "Hello from remote server!"

# 远程HTTP请求
result = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://api.example.com/data
    captures:
        response_id: ["jsonpath", "$.id"]
'''

[打印],内容: "远程请求结果: ${result}"
```

### 3. 运行测试

```bash
pytest-dsl your_test.dsl
```

## 服务器配置

### 命令行参数

```bash
python -m pytest_dsl.remote.keyword_server [OPTIONS]

选项:
  --host TEXT        服务器监听地址 (默认: localhost)
  --port INTEGER     服务器监听端口 (默认: 8270)
  --api-key TEXT     API密钥，用于客户端认证
  --help            显示帮助信息
```

### 环境变量配置

```bash
# 设置默认配置
export PYTEST_DSL_REMOTE_HOST=0.0.0.0
export PYTEST_DSL_REMOTE_PORT=8270
export PYTEST_DSL_REMOTE_API_KEY=your_secret_key
```

### 使用pyproject.toml启动

在项目的`pyproject.toml`中添加：

```toml
[tool.pytest-dsl.scripts]
start-remote-server = "python -m pytest_dsl.remote.keyword_server --host 0.0.0.0 --port 8270"
```

然后使用：

```bash
pytest-dsl start-remote-server
```

## 客户端使用

### DSL文件中的远程服务器声明

```dsl
# 基本连接
@remote: "http://localhost:8270/" as server1

# 带认证的连接
@remote: "http://localhost:8270/" as server1 with api_key="your_secret_key"

# 多个远程服务器
@remote: "http://server1:8270/" as server1
@remote: "http://server2:8270/" as server2
```

### 远程关键字调用语法

```dsl
# 基本语法
remote_server|[关键字名称],参数1: 值1,参数2: 值2

# 带返回值
result = remote_server|[关键字名称],参数: 值

# 复杂参数
remote_server|[HTTP请求],配置: '''
    method: POST
    url: https://api.example.com
    request:
        json:
            name: "test"
            value: 123
'''
```

## DSL语法

### 支持的关键字

所有内置关键字都支持远程执行：

- **基础关键字**: 打印、返回结果、等待
- **HTTP关键字**: HTTP请求（完整支持capture和会话）
- **断言关键字**: 断言、JSON断言、类型断言、数据比较
- **工具关键字**: 生成随机字符串、生成随机数、字符串操作
- **时间关键字**: 获取当前时间
- **全局变量**: 设置/获取/删除全局变量
- **JSON操作**: JSON提取、JSON断言

### 变量捕获示例

```dsl
@remote: "http://localhost:8270/" as remote_server

# 远程HTTP请求with变量捕获
result = remote_server|[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    captures:
        post_id: ["jsonpath", "$.id"]
        post_title: ["jsonpath", "$.title"]
        user_id: ["jsonpath", "$.userId"]
    asserts:
        - ["status", "eq", 200]
'''

# 使用捕获的变量（注意：远程捕获的变量需要通过返回值访问）
[打印],内容: "远程捕获结果: ${result}"

# 远程JSON提取
extracted_value = remote_server|[JSON提取],JSON数据: '{"name": "test"}',JSONPath: "$.name",变量名: "remote_name"
[打印],内容: "提取的值: ${extracted_value}"
```

### 会话管理示例

```dsl
@remote: "http://localhost:8270/" as remote_server

# 远程会话设置
remote_server|[HTTP请求],客户端: "default",会话: "test_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies/set/session_id/remote_123
'''

# 远程会话验证
remote_server|[HTTP请求],客户端: "default",会话: "test_session",配置: '''
    method: GET
    url: https://httpbin.org/cookies
    asserts:
        - ["jsonpath", "$.cookies.session_id", "eq", "remote_123"]
'''
```

### 全局变量示例

```dsl
@remote: "http://localhost:8270/" as remote_server

# 远程设置全局变量
remote_server|[设置全局变量],变量名: "remote_config",值: "production"

# 远程获取全局变量
config = remote_server|[获取全局变量],变量名: "remote_config"
[打印],内容: "远程配置: ${config}"

# 注意：远程和本地的全局变量是独立的
[设置全局变量],变量名: "local_config",值: "development"
local_config = [获取全局变量],变量名: "local_config"
[打印],内容: "本地配置: ${local_config}"
```

## 高级功能

### 多服务器协作

```dsl
@remote: "http://server1:8270/" as server1
@remote: "http://server2:8270/" as server2

# 在不同服务器上执行操作
server1|[设置全局变量],变量名: "shared_data",值: "from_server1"
server2|[设置全局变量],变量名: "shared_data",值: "from_server2"

# 获取各自的数据
data1 = server1|[获取全局变量],变量名: "shared_data"
data2 = server2|[获取全局变量],变量名: "shared_data"

[打印],内容: "Server1数据: ${data1}"
[打印],内容: "Server2数据: ${data2}"
```

### 错误处理

```dsl
@remote: "http://localhost:8270/" as remote_server

# 使用try-catch处理远程错误
try
    result = remote_server|[HTTP请求],客户端: "default",配置: '''
        method: GET
        url: https://invalid-url-that-will-fail.com
    '''
catch error
    [打印],内容: "远程请求失败: ${error}"
end
```

### 条件执行

```dsl
@remote: "http://localhost:8270/" as remote_server

# 根据条件选择本地或远程执行
@if: "${environment} == 'production'"
    result = remote_server|[HTTP请求],客户端: "default",配置: '''
        method: GET
        url: https://api.production.com/health
    '''
@else
    result = [HTTP请求],客户端: "default",配置: '''
        method: GET
        url: https://api.staging.com/health
    '''
@endif

[打印],内容: "健康检查结果: ${result}"
```

## 故障排除

### 常见问题

#### 1. 连接失败

```
错误: 无法连接到远程服务器 http://localhost:8270/
```

**解决方案**:
- 确认远程服务器已启动
- 检查网络连接和防火墙设置
- 验证地址和端口是否正确

#### 2. API密钥认证失败

```
错误: 远程关键字执行失败: API密钥验证失败
```

**解决方案**:
- 确认服务器启动时设置了正确的API密钥
- 在DSL文件中正确配置API密钥

#### 3. 变量捕获问题

```
问题: 远程执行的关键字无法捕获变量到本地上下文
```

**解决方案**:
- 远程捕获的变量通过返回值传递，不会自动设置到本地上下文
- 使用返回值来访问捕获的数据

#### 4. 会话状态丢失

```
问题: 远程执行的HTTP请求无法保持会话状态
```

**解决方案**:
- 确保在同一个远程服务器上执行相关的HTTP请求
- 使用相同的会话名称
- 会话状态在远程服务器上维护，不会同步到本地

### 调试技巧

#### 启用详细日志

```bash
# 启动服务器时启用调试日志
python -m pytest_dsl.remote.keyword_server --host localhost --port 8270 --debug

# 运行测试时启用详细输出
pytest-dsl your_test.dsl --verbose
```

#### 检查服务器状态

```bash
# 检查服务器是否响应
curl -X POST http://localhost:8270/ \
  -H "Content-Type: application/json" \
  -d '{"action": "list_keywords"}'
```

#### 网络诊断

```bash
# 检查端口是否开放
telnet localhost 8270

# 检查网络连接
ping your-remote-server
```

---

## 相关文档

- [远程关键字开发指南](remote-keywords-development.md)
- [关键字参考文档](keyword-reference.md)
- [配置指南](configuration.md)
