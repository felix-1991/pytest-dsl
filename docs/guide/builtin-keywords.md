# 内置关键字

pytest-dsl提供了丰富的内置关键字，涵盖了常见的测试操作。本章将详细介绍这些内置关键字的使用方法。

## 关键字分类

内置关键字按功能分为以下几类：

1. **基础操作** - 打印、等待、断言等
2. **HTTP测试** - API接口测试相关
3. **数据处理** - 数据比较、JSON操作、字符串处理、类型验证等
4. **变量管理** - 全局变量操作
5. **工具类** - 随机数生成、时间获取、日志记录等
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
- `秒数` (必需): 等待的时间（秒），支持小数

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
- `客户端` (必需): HTTP客户端名称，对应YAML变量文件中的客户端配置
- `配置` (必需): YAML格式的请求配置，包含请求、捕获和断言
- `会话` (可选): 会话名称，用于在多个请求间保持会话状态
- `保存响应` (可选): 将完整响应保存到指定变量名中
- `禁用授权` (可选): 禁用客户端配置中的授权机制，默认为false
- `模板` (可选): 使用YAML变量文件中定义的请求模板
- `断言重试次数` (可选): 断言失败时的重试次数，默认为0
- `断言重试间隔` (可选): 断言重试间隔时间（秒），默认为1

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

### 字符串操作

执行各种字符串操作。

```python
# 去除空格（默认操作）
text = "  hello world  "
cleaned = [字符串操作], 字符串: ${text}  # 默认为strip操作
[打印], 内容: "清理后: '${cleaned}'"

# 字符串拼接
first_name = "张"
last_name = "三"
full_name = [字符串操作], 操作: "concat", 字符串: ${first_name}, 参数1: ${last_name}
[打印], 内容: "全名: ${full_name}"

# 字符串替换
original = "Hello World"
replaced = [字符串操作], 操作: "replace", 字符串: ${original}, 参数1: "World", 参数2: "Python"
[打印], 内容: "替换后: ${replaced}"

# 字符串分割
text = "apple,banana,orange"
fruits = [字符串操作], 操作: "split", 字符串: ${text}, 参数1: ","
[打印], 内容: "水果列表: ${fruits}"

# 大小写转换
text = "Hello World"
upper_text = [字符串操作], 操作: "upper", 字符串: ${text}
lower_text = [字符串操作], 操作: "lower", 字符串: ${text}
[打印], 内容: "大写: ${upper_text}, 小写: ${lower_text}"
```

**参数：**
- `操作` (可选): 操作类型，默认为"strip"
  - `concat`: 拼接字符串
  - `replace`: 替换字符串
  - `split`: 分割字符串
  - `upper`: 转换为大写
  - `lower`: 转换为小写
  - `strip`: 去除首尾空格
- `字符串` (必需): 要操作的字符串
- `参数1` (可选): 操作参数1，根据操作类型不同而不同
- `参数2` (可选): 操作参数2，根据操作类型不同而不同

**返回值：** 操作后的字符串

### 类型断言

验证值的数据类型。

```python
# 基本类型检查
name = "pytest-dsl"
age = 25
is_active = True
scores = [85, 90, 78]
user_info = {"name": "张三", "age": 30}

[类型断言], 值: ${name}, 类型: "string", 消息: "name应该是字符串"
[类型断言], 值: ${age}, 类型: "number", 消息: "age应该是数字"
[类型断言], 值: ${is_active}, 类型: "boolean", 消息: "is_active应该是布尔值"
[类型断言], 值: ${scores}, 类型: "list", 消息: "scores应该是列表"
[类型断言], 值: ${user_info}, 类型: "object", 消息: "user_info应该是对象"

# 检查null值
empty_value = None
[类型断言], 值: ${empty_value}, 类型: "null", 消息: "empty_value应该是null"
```

**参数：**
- `值` (必需): 要检查的值
- `类型` (必需): 预期的类型
  - `string`: 字符串类型
  - `number`: 数字类型（整数或浮点数）
  - `boolean`: 布尔类型
  - `list`: 列表类型
  - `object`: 对象/字典类型
  - `null`: 空值类型
- `消息` (可选): 断言失败时的错误消息

**返回值：** 断言结果 (True/False)

### JSON提取

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
total_count = [JSON提取], JSON数据: ${json_data}, JSONPath: "$.total"
[打印], 内容: "总用户数: ${total_count}"

# 提取第一个用户的姓名
first_user_name = [JSON提取], JSON数据: ${json_data}, JSONPath: "$.users[0].name"
[打印], 内容: "第一个用户: ${first_user_name}"

# 提取所有用户的邮箱
all_emails = [JSON提取], JSON数据: ${json_data}, JSONPath: "$.users[*].email"
[打印], 内容: "所有邮箱: ${all_emails}"
```

**参数：**
- `JSON数据` (必需): JSON数据对象
- `JSONPath` (必需): JSONPath表达式
- `变量名` (可选): 存储提取值的变量名

**返回值：** 提取的值或值列表

### JSON断言

执行JSON断言验证。

```python
# 验证JSON数据中的值
response_data = {"status": "success", "code": 200, "data": {"id": 123}}

# 基本断言
[JSON断言], JSON数据: ${response_data}, JSONPath: "$.status", 预期值: "success"

# 使用不同操作符
[JSON断言], JSON数据: ${response_data}, JSONPath: "$.code", 预期值: 200, 操作符: "=="
[JSON断言], JSON数据: ${response_data}, JSONPath: "$.data.id", 预期值: 100, 操作符: ">"

# 自定义错误消息
[JSON断言], JSON数据: ${response_data}, JSONPath: "$.status", 预期值: "success", 消息: "API状态应该为成功"
```

**参数：**
- `JSON数据` (必需): JSON数据对象
- `JSONPath` (必需): JSONPath表达式
- `预期值` (必需): 预期的值
- `操作符` (可选): 比较操作符，默认为"=="
- `消息` (可选): 断言失败时的错误消息

**返回值：** 断言结果 (True/False)

## 变量管理关键字

### 设置全局变量

设置可在不同测试用例间共享的全局变量。

```python
# 设置全局变量
[设置全局变量], 变量名: "api_token", 值: "abc123"

# 在其他测试中使用
token = [获取全局变量], 变量名: "api_token"
[打印], 内容: "当前token: ${token}"
```

**参数：**
- `变量名` (必需): 全局变量的名称
- `值` (必需): 全局变量的值

**返回值：** 无

### 获取全局变量

获取之前设置的全局变量。

```python
# 获取全局变量
current_user = [获取全局变量], 变量名: "current_user"
[打印], 内容: "当前用户: ${current_user}"
```

**参数：**
- `变量名` (必需): 全局变量的名称

**返回值：** 全局变量的值

### 删除全局变量

删除指定的全局变量。

```python
# 设置全局变量
[设置全局变量], 变量名: "temp_token", 值: "abc123"

# 使用全局变量
token = [获取全局变量], 变量名: "temp_token"
[打印], 内容: "临时token: ${token}"

# 删除全局变量
[删除全局变量], 变量名: "temp_token"

# 尝试获取已删除的变量会失败
# token = [获取全局变量], 变量名: "temp_token"  # 会报错
```

**参数：**
- `变量名` (必需): 要删除的全局变量名称

**返回值：** 无

### 清除所有全局变量

清除所有已设置的全局变量。

```python
# 设置多个全局变量
[设置全局变量], 变量名: "user_id", 值: 123
[设置全局变量], 变量名: "session_token", 值: "xyz789"
[设置全局变量], 变量名: "api_key", 值: "key123"

# 清除所有全局变量
[清除所有全局变量]

# 所有变量都已被清除
# user_id = [获取全局变量], 变量名: "user_id"  # 会报错
```

**参数：** 无

**返回值：** 无

## 工具类关键字

### 生成随机数

生成指定范围内的随机数。

```python
# 生成默认范围的随机数（0-100）
random_num = [生成随机数]
[打印], 内容: "随机数: ${random_num}"

# 生成指定范围的随机数
small_num = [生成随机数], 最小值: 1, 最大值: 10
[打印], 内容: "小随机数: ${small_num}"

# 生成浮点数
float_num = [生成随机数], 最小值: 0, 最大值: 1, 小数位数: 2
[打印], 内容: "浮点随机数: ${float_num}"
```

**参数：**
- `最小值` (可选): 随机数的最小值，默认为0
- `最大值` (可选): 随机数的最大值，默认为100
- `小数位数` (可选): 小数位数，0表示整数，默认为0

**返回值：** 生成的随机数（整数或浮点数）

### 生成随机字符串

生成指定长度和类型的随机字符串。

```python
# 生成默认随机字符串（8位字母数字混合）
random_str = [生成随机字符串]
[打印], 内容: "随机字符串: ${random_str}"

# 生成指定长度的字符串
long_str = [生成随机字符串], 长度: 16
[打印], 内容: "长随机字符串: ${long_str}"

# 生成纯字母字符串
letter_str = [生成随机字符串], 长度: 10, 类型: "letters"
[打印], 内容: "字母字符串: ${letter_str}"

# 生成纯数字字符串
digit_str = [生成随机字符串], 长度: 6, 类型: "digits"
[打印], 内容: "数字字符串: ${digit_str}"
```

**参数：**
- `长度` (可选): 字符串长度，默认为8
- `类型` (可选): 字符类型，默认为"alphanumeric"
  - `letters`: 纯字母
  - `digits`: 纯数字
  - `alphanumeric`: 字母数字混合
  - `all`: 包含特殊字符

**返回值：** 生成的随机字符串

### 获取当前时间

获取当前时间，支持多种格式和时区。

```python
# 获取时间戳（默认）
timestamp = [获取当前时间]
[打印], 内容: "时间戳: ${timestamp}"

# 获取格式化时间（默认北京时间）
formatted_time = [获取当前时间], 格式: "%Y-%m-%d %H:%M:%S"
[打印], 内容: "北京时间: ${formatted_time}"

# 获取其他时区时间
utc_time = [获取当前时间], 格式: "%Y-%m-%d %H:%M:%S", 时区: "UTC"
[打印], 内容: "UTC时间: ${utc_time}"

# 获取本地时间
local_time = [获取当前时间], 格式: "%Y-%m-%d %H:%M:%S", 时区: "local"
[打印], 内容: "本地时间: ${local_time}"
```

**参数：**
- `格式` (可选): 时间格式，默认为"timestamp"返回时间戳
- `时区` (可选): 时区，默认为"Asia/Shanghai"

**常用时间格式：**
- `%Y-%m-%d`: 年-月-日
- `%H:%M:%S`: 时:分:秒
- `%Y-%m-%d %H:%M:%S`: 完整日期时间

**返回值：** 格式化的时间字符串或时间戳

### 日志

记录不同级别的日志信息。

```python
# 记录信息日志（默认级别）
[日志], 消息: "测试开始执行"

# 记录不同级别的日志
[日志], 级别: "DEBUG", 消息: "调试信息：变量值为 ${variable}"
[日志], 级别: "INFO", 消息: "信息：用户登录成功"
[日志], 级别: "WARNING", 消息: "警告：API响应时间较长"
[日志], 级别: "ERROR", 消息: "错误：数据库连接失败"
[日志], 级别: "CRITICAL", 消息: "严重错误：系统崩溃"
```

**参数：**
- `级别` (可选): 日志级别，默认为"INFO"
  - `DEBUG`: 调试信息
  - `INFO`: 一般信息
  - `WARNING`: 警告信息
  - `ERROR`: 错误信息
  - `CRITICAL`: 严重错误
- `消息` (必需): 日志消息内容

**返回值：** 无

### 返回结果

在函数或测试用例中返回指定的结果值。

```python
# 在函数中返回结果
function 计算总和 (a, b) do
    result = a + b
    [返回结果], 结果: ${result}
end

# 调用函数
sum_value = [计算总和], a: 10, b: 20
[打印], 内容: "总和: ${sum_value}"

# 在测试用例中返回测试结果
@name: "API测试"
# ... 执行测试步骤 ...
test_result = {"status": "passed", "message": "所有测试通过"}
[返回结果], 结果: ${test_result}
```

**参数：**
- `结果` (必需): 要返回的结果值

**返回值：** 指定的结果值

## 系统操作关键字

### 执行命令

执行系统命令并获取结果。

```python
# 执行简单命令
result = [执行命令], 命令: "echo 'Hello World'"
[打印], 内容: "命令输出: ${result.stdout}"

# 执行带超时的命令
result = [执行命令], 命令: "ping -c 3 google.com", 超时: 10
[断言], 条件: "${result.returncode} == 0", 消息: "ping命令应该成功"

# 执行复杂命令
result = [执行命令], 命令: "ls -la /tmp", 捕获输出: true
[打印], 内容: "目录内容: ${result.stdout}"
```

**参数：**
- `命令` (必需): 要执行的系统命令
- `超时` (可选): 命令执行超时时间（秒），默认60
- `捕获输出` (可选): 是否捕获命令输出，默认true

**返回值：** 包含返回码、标准输出和标准错误的字典

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
| HTTP请求 | API测试 | 客户端, 配置, 会话, 保存响应, 禁用授权, 模板, 断言重试次数, 断言重试间隔 | 响应对象 |
| 数据比较 | 值比较 | 实际值, 预期值, 操作符, 消息 | 布尔值 |
| JSON提取 | JSON数据提取 | JSON数据, JSONPath, 变量名 | 提取值 |
| JSON断言 | JSON数据断言 | JSON数据, JSONPath, 预期值, 操作符, 消息 | 布尔值 |
| 字符串操作 | 字符串处理 | 操作, 字符串, 参数1, 参数2 | 处理后字符串 |
| 类型断言 | 类型验证 | 值, 类型, 消息 | 布尔值 |
| 设置全局变量 | 变量存储 | 变量名, 值 | 无 |
| 获取全局变量 | 变量获取 | 变量名 | 变量值 |
| 执行命令 | 系统命令 | 命令, 超时, 捕获输出 | 执行结果 |
| 生成随机数 | 随机数生成 | 最小值, 最大值, 小数位数 | 随机数 |
| 生成随机字符串 | 随机字符串生成 | 长度, 类型 | 随机字符串 |
| 获取当前时间 | 时间获取 | 格式, 时区 | 时间字符串/时间戳 |
| 日志 | 日志记录 | 级别, 消息 | 无 |
| 返回结果 | 结果返回 | 结果 | 指定结果 |
| 删除全局变量 | 变量删除 | 变量名 | 无 |
| 清除所有全局变量 | 变量清理 | 无 | 无 |

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