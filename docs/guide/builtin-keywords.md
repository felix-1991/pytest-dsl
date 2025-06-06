# 内置关键字

pytest-dsl提供了丰富的内置关键字，涵盖了常见的测试操作。本章将详细介绍这些内置关键字的使用方法。

## 关键字分类

内置关键字按功能分为以下几类：

1. **基础操作** - 打印、等待、断言等
2. **HTTP测试** - API接口测试相关
3. **数据处理** - 数据比较、类型转换等
4. **流程控制** - 条件判断、循环辅助
5. **变量管理** - 全局变量操作
6. **系统操作** - 命令执行、文件操作

## 基础操作关键字

### 打印 (Print)

用于输出信息到控制台，是最常用的调试和日志记录关键字。

```python
# 基本用法
[打印], 内容: "Hello, World!"

# 使用变量
message = "测试消息"
[打印], 内容: ${message}

# 组合信息
name = "张三"
age = 30
[打印], 内容: "用户姓名: ${name}, 年龄: ${age}"
```

**参数：**
- `内容` (必需): 要打印的内容，支持字符串插值

**返回值：** 无

### 等待 (Wait)

暂停执行指定的时间，常用于等待异步操作完成。

```python
# 等待3秒
[等待], 秒数: 3

# 等待较短时间
[等待], 秒数: 0.5

# 使用变量控制等待时间
delay = 2
[等待], 秒数: ${delay}
```

**参数：**
- `秒数` (必需): 等待的秒数，支持小数

**返回值：** 无

### 断言 (Assert)

验证条件是否为真，是测试验证的核心关键字。

```python
# 简单断言
[断言], 条件: "1 == 1", 消息: "数学基本定律错误"

# 使用变量
result = 10
expected = 10
[断言], 条件: "${result} == ${expected}", 消息: "计算结果不匹配"

# 复杂条件
status_code = 200
[断言], 条件: "${status_code} >= 200 and ${status_code} < 300", 消息: "HTTP状态码不在成功范围"

# 字符串包含检查
response_text = "success"
[断言], 条件: "'success' in '${response_text}'", 消息: "响应中未包含成功标识"
```

**参数：**
- `条件` (必需): 要验证的条件表达式，应返回True/False
- `消息` (可选): 断言失败时显示的错误消息

**返回值：** 无（失败时抛出异常）

## HTTP测试关键字

### HTTP请求 (HTTP Request)

执行HTTP请求，是API测试的核心关键字。

```python
# 简单GET请求
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
'''

# POST请求with JSON数据
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: https://api.example.com/users
    request:
        json:
            name: "张三"
            email: "zhangsan@example.com"
    captures:
        user_id: ["jsonpath", "$.id"]
    asserts:
        - ["status", "eq", 201]
        - ["jsonpath", "$.name", "eq", "张三"]
'''

# 带认证的请求
token = "abc123"
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/profile
    request:
        headers:
            Authorization: "Bearer ${token}"
    asserts:
        - ["status", "eq", 200]
'''
```

**参数：**
- `客户端` (必需): HTTP客户端名称
- `配置` (必需): YAML格式的请求配置
- `步骤名称` (可选): 测试步骤的描述名称

**支持的配置选项：**
- `method`: HTTP方法 (GET, POST, PUT, DELETE等)
- `url`: 请求URL
- `request`: 请求参数
  - `headers`: 请求头
  - `params`: URL参数
  - `json`: JSON请求体
  - `data`: 表单数据
  - `files`: 文件上传
- `captures`: 响应数据捕获
- `asserts`: 断言验证

**返回值：** 响应对象（包含状态码、头部、内容等）

### 设置HTTP客户端

在配置文件中定义HTTP客户端：

```yaml
# config.yaml
http_clients:
  default:
    base_url: "https://api.example.com"
    timeout: 30
    headers:
      Content-Type: "application/json"
      User-Agent: "pytest-dsl/1.0"
  
  auth_server:
    base_url: "https://auth.example.com"
    timeout: 60
    headers:
      Accept: "application/json"
```

## 数据处理关键字

### 数据比较 (Data Compare)

比较两个值并验证关系。

```python
# 基本比较
actual = 10
expected = 10
[数据比较], 实际值: ${actual}, 预期值: ${expected}, 操作符: "=="

# 不同操作符
score = 85
[数据比较], 实际值: ${score}, 预期值: 80, 操作符: ">", 消息: "分数应该大于80"

# 字符串比较
name = "pytest-dsl"
[数据比较], 实际值: ${name}, 预期值: "pytest-dsl", 操作符: "=="
```

**参数：**
- `实际值` (必需): 实际的值
- `预期值` (必需): 预期的值
- `操作符` (可选): 比较操作符，默认为"=="
- `消息` (可选): 比较失败时的错误消息

**支持的操作符：**
- `==`: 等于
- `!=`: 不等于
- `>`: 大于
- `<`: 小于
- `>=`: 大于等于
- `<=`: 小于等于
- `in`: 包含
- `not_in`: 不包含

**返回值：** 比较结果 (True/False)

### JSON路径提取

从JSON数据中提取特定值。

```python
# 假设有JSON响应数据
json_data = {
    "users": [
        {"id": 1, "name": "张三", "email": "zhangsan@example.com"},
        {"id": 2, "name": "李四", "email": "lisi@example.com"}
    ],
    "total": 2
}

# 提取总数
total_count = [JSON路径提取], 数据: ${json_data}, 路径: "$.total"
[打印], 内容: "总用户数: ${total_count}"

# 提取第一个用户的姓名
first_user_name = [JSON路径提取], 数据: ${json_data}, 路径: "$.users[0].name"
[打印], 内容: "第一个用户: ${first_user_name}"

# 提取所有用户的邮箱
all_emails = [JSON路径提取], 数据: ${json_data}, 路径: "$.users[*].email"
[打印], 内容: "所有邮箱: ${all_emails}"
```

**参数：**
- `数据` (必需): JSON数据对象
- `路径` (必需): JSONPath表达式

**返回值：** 提取的值或值列表

## 变量管理关键字

### 设置全局变量

设置可在不同测试用例间共享的全局变量。

```python
# 设置全局变量
[设置全局变量], 变量名: "api_token", 值: "abc123456"
[设置全局变量], 变量名: "test_user_id", 值: 1001

# 设置复杂数据
user_info = {"name": "测试用户", "role": "admin"}
[设置全局变量], 变量名: "current_user", 值: ${user_info}
```

**参数：**
- `变量名` (必需): 全局变量的名称
- `值` (必需): 全局变量的值

**返回值：** 无

### 获取全局变量

获取之前设置的全局变量值。

```python
# 获取全局变量
token = [获取全局变量], 变量名: "api_token"
[打印], 内容: "当前token: ${token}"

# 获取并使用
user_id = [获取全局变量], 变量名: "test_user_id"
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/users/${user_id}
    asserts:
        - ["status", "eq", 200]
'''
```

**参数：**
- `变量名` (必需): 要获取的全局变量名称

**返回值：** 全局变量的值

## 系统操作关键字

### 执行命令

执行系统命令并捕获输出。

```python
# 简单命令执行
result = [执行命令], 命令: "echo 'Hello World'"
[打印], 内容: "命令输出: ${result.stdout}"

# 带超时的命令
result = [执行命令], 命令: "ping -c 3 google.com", 超时: 30
[打印], 内容: "Ping结果: ${result.returncode}"

# 不捕获输出
[执行命令], 命令: "ls -la", 捕获输出: False
```

**参数：**
- `命令` (必需): 要执行的系统命令
- `超时` (可选): 命令执行超时时间（秒），默认60秒
- `捕获输出` (可选): 是否捕获命令输出，默认True

**返回值：** 包含返回码、标准输出和标准错误的字典

```python
{
    "returncode": 0,
    "stdout": "命令的标准输出",
    "stderr": "命令的错误输出"
}
```

## 高级用法示例

### 组合使用关键字

```python
@name: "用户注册和验证流程"

# 准备测试数据
user_data = {
    "username": "testuser123",
    "email": "testuser123@example.com",
    "password": "securepassword"
}

# 1. 注册新用户
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/register
    request:
        json: ${user_data}
    captures:
        user_id: ["jsonpath", "$.user_id"]
        activation_token: ["jsonpath", "$.activation_token"]
    asserts:
        - ["status", "eq", 201]
        - ["jsonpath", "$.message", "eq", "用户注册成功"]
'''

[打印], 内容: "用户注册成功，ID: ${user_id}"

# 2. 验证用户数据
[数据比较], 实际值: ${user_id}, 预期值: 0, 操作符: ">", 消息: "用户ID应该大于0"

# 3. 激活用户账户
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/activate
    request:
        json:
            user_id: ${user_id}
            token: ${activation_token}
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.status", "eq", "activated"]
'''

# 4. 登录测试
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/login
    request:
        json:
            username: "${user_data.username}"
            password: "${user_data.password}"
    captures:
        access_token: ["jsonpath", "$.access_token"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.access_token", "not_empty"]
'''

# 5. 保存token供后续使用
[设置全局变量], 变量名: "auth_token", 值: ${access_token}

# 6. 验证登录状态
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/profile
    request:
        headers:
            Authorization: "Bearer ${access_token}"
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.username", "eq", "${user_data.username}"]
'''

[打印], 内容: "用户注册和验证流程完成"
```

### 错误处理模式

```python
@name: "带错误处理的API测试"

# 测试不存在的资源
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: /api/users/99999
    asserts:
        - ["status", "eq", 404]
        - ["jsonpath", "$.error", "eq", "用户不存在"]
'''

# 测试无效数据
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/users
    request:
        json:
            name: ""  # 空名称应该失败
            email: "invalid-email"  # 无效邮箱
    asserts:
        - ["status", "eq", 400]
        - ["jsonpath", "$.errors", "length", "gt", 0]
'''

# 测试权限验证
[HTTP请求], 客户端: "default", 配置: '''
    method: DELETE
    url: /api/admin/users/1
    request:
        headers:
            Authorization: "Bearer invalid_token"
    asserts:
        - ["status", "eq", 401]
        - ["jsonpath", "$.error", "eq", "未授权访问"]
'''
```

## 关键字参考速查

| 关键字名称 | 主要用途 | 必需参数 | 返回值 |
|-----------|----------|----------|--------|
| 打印 | 输出信息 | 内容 | 无 |
| 等待 | 延时执行 | 秒数 | 无 |
| 断言 | 条件验证 | 条件, 消息 | 无 |
| HTTP请求 | API测试 | 客户端, 配置 | 响应对象 |
| 数据比较 | 值比较 | 实际值, 预期值 | 布尔值 |
| 设置全局变量 | 变量存储 | 变量名, 值 | 无 |
| 获取全局变量 | 变量获取 | 变量名 | 变量值 |
| 执行命令 | 系统命令 | 命令 | 执行结果 |

## 最佳实践

### 1. 合理使用打印输出

```python
# 好的做法 - 提供有意义的信息
[打印], 内容: "开始执行用户登录测试"
[打印], 内容: "用户ID: ${user_id}, 状态: ${status}"

# 避免 - 过度输出或无意义信息
[打印], 内容: "1"
[打印], 内容: "test"
```

### 2. 断言消息要清晰

```python
# 好的断言消息
[断言], 条件: "${status_code} == 200", 消息: "API调用应该返回200状态码，实际返回: ${status_code}"

# 避免 - 模糊的错误消息
[断言], 条件: "${status_code} == 200", 消息: "错误"
```

### 3. HTTP请求配置要完整

```python
# 好的做法 - 包含必要的断言和数据捕获
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/users
    request:
        json: ${user_data}
    captures:
        user_id: ["jsonpath", "$.id"]
    asserts:
        - ["status", "eq", 201]
        - ["jsonpath", "$.id", "not_empty"]
        - ["jsonpath", "$.name", "eq", "${user_data.name}"]
'''

# 避免 - 缺少验证的请求
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/users
    request:
        json: ${user_data}
'''
```

### 4. 全局变量命名规范

```python
# 好的命名 - 清晰表达用途
[设置全局变量], 变量名: "auth_token", 值: ${token}
[设置全局变量], 变量名: "test_user_id", 值: ${user_id}

# 避免 - 模糊的变量名
[设置全局变量], 变量名: "var1", 值: ${token}
[设置全局变量], 变量名: "temp", 值: ${user_id}
```

## 下一步

- 学习[自定义关键字](./custom-keywords)创建项目特定的测试步骤
- 查看[HTTP API测试](./http-testing)深入了解API测试技巧
- 阅读[变量和数据类型](./variables)掌握数据处理方法 