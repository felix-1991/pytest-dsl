# pytest-dsl: 强大的关键字驱动测试自动化框架

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI Version](https://img.shields.io/pypi/v/pytest-dsl.svg)](https://pypi.org/project/pytest-dsl/)

> 🚀 **让测试自动化变得简单直观** - 使用自然语言风格的DSL编写测试，无需复杂编程技能

pytest-dsl 是一个基于 pytest 的关键字驱动测试框架，通过自定义领域特定语言（DSL）让测试编写更接近自然语言。仓库当前直接提供 DSL 执行、HTTP/API 测试、远程关键字调用、变量管理和 pytest 集成能力；UI 测试、HTML/Allure 报告、编辑器增强等能力主要通过配套扩展或 pytest 生态实现。

## ✨ 核心特性

- 🎯 **门槛上手低** - 自然语言风格，只需少量编程基础
- 🔧 **高度可扩展** - 轻松创建自定义关键字，支持参数默认值
- 🌐 **分布式执行** - 支持远程关键字调用
- 🔄 **无缝集成** - 完美兼容pytest生态
- 📊 **报告生态兼容** - 可结合 pytest 生态生成 HTML、Allure 等报告
- 🛡️ **配置与变量管理** - 支持 YAML 变量、认证配置和上下文共享
- ⚡ **智能简化** - 参数默认值让DSL更加简洁易读

## 🚀 5分钟快速开始

### 第一步：安装

```bash
# 使用 pip 安装
pip install pytest-dsl

# 或使用 uv 安装（推荐）
uv pip install pytest-dsl
```

### 第二步：创建第一个测试

创建文件 `hello.dsl`：

```python
@name: "我的第一个测试"
@description: "学习pytest-dsl的第一步"

# 定义变量
message = "Hello, pytest-dsl!"
count = 3

# 打印欢迎消息
[打印], 内容: ${message}

# 简单循环
for i in range(1, ${count} + 1) do
    [打印], 内容: "第 ${i} 次循环"
end

# 测试断言
[断言], 条件: "${count} == 3", 消息: "计数器应该等于3"

teardown do
    [打印], 内容: "测试完成！"
end
```

### 第三步：运行测试

```bash
# 直接运行DSL文件
pytest-dsl hello.dsl

# 运行目录下所有DSL文件
pytest-dsl tests/
```

🎉 **恭喜！** 您已经成功运行了第一个pytest-dsl测试！

## 📚 基础教程

### 1. 基本语法入门

#### 变量和数据类型

```python
# 字符串变量
name = "pytest-dsl"
version = "1.0.0"

# 数字变量
port = 8080

# 布尔值变量
is_enabled = True
is_disabled = False

# 列表
users = ["alice", "bob", "charlie"]

# 字典
user_info = {"name": "张三", "age": 30, "city": "北京"}

# 嵌套字典
config = {
    "database": {
        "host": "localhost",
        "port": 3306,
        "name": "test_db"
    },
    "api": {
        "base_url": "https://api.example.com",
        "timeout": 30
    }
}

# 访问字典值
username = ${user_info["name"]}
db_host = ${config["database"]["host"]}
```

#### 流程控制

```python
# 条件判断
status = "success"
if status == "success" do
    [打印], 内容: "测试通过"
else
    [打印], 内容: "测试失败"
end

# 使用布尔值的条件判断
is_ready = True
if ${is_ready} do
    [打印], 内容: "系统就绪"
end

# 循环结构
num = 4
for i in range(1, num) do
    [打印], 内容: "执行第 ${i} 次"
end

# 循环中的break和continue
for j in range(1, 11) do
    # 跳过偶数
    if ${j} % 2 == 0 do
        continue
    end
    
    # 当达到7时退出循环
    if ${j} == 7 do
        [打印], 内容: "达到7，退出循环"
        break
    end
    
    [打印], 内容: "奇数: ${j}"
end
```

### 2. 内置关键字详解

#### 基础关键字

```python
# 打印输出
[打印], 内容: "Hello World"

# 断言测试
[断言], 条件: "1 + 1 == 2", 消息: "数学计算错误"

# 等待
[等待], 秒数: 2

# 生成随机数
random_num = [生成随机数], 最小值: 1, 最大值: 100
[打印], 内容: "随机数: ${random_num}"
```

#### 变量操作

```python
[设置全局变量], 变量名: "test_env", 值: "development"

# 获取全局变量
env = [获取全局变量], 变量名: "test_env"
[打印], 内容: "当前环境: ${env['result']}"
```

### 3. 自定义关键字（函数）

自定义关键字让您可以封装复用的测试逻辑：

```python
@name: "自定义关键字示例"

# 定义一个计算器关键字
function 计算器 (操作, 数字1, 数字2=0) do
    if ${操作} == "加法" do
        [打印],内容: "执行加法操作"
        结果 = ${数字1} + ${数字2}
    else
        结果 = 12
    end

    [打印], 内容: "${数字1} ${操作} ${数字2} = ${结果}"
    return ${结果}
end

# 使用自定义关键字
sum_result = [计算器], 操作: "加法", 数字1: 10, 数字2: 5
product_result = [计算器], 操作: "其他", 数字1: 3, 数字2: 4

# 验证结果
[断言], 条件: "${sum_result} == 15", 消息: "加法计算错误"
[断言], 条件: "${product_result} == 12", 消息: "其他计算错误"
```

#### 资源文件复用

将常用关键字保存在资源文件中（`.resource`），实现跨项目复用：

**创建资源文件 `utils.resource`：**

```python
@name: "通用工具关键字"

# 定义一个简单的关键字（函数）
function 拼接字符串 (前缀, 后缀="默认后缀") do
    # 直接使用关键字参数
    [打印],内容: "拼接前缀: ${前缀} 和后缀: ${后缀}"

    # 保存到变量中
    结果变量 = "${前缀}${后缀}"
    [打印],内容: "拼接结果: ${结果变量}"

    # 返回结果
    return ${结果变量}
end
```

**在测试中使用资源文件：**

```python
@name: "使用资源文件示例"
@import: "utils.resource"

# 使用自定义关键字
问候语 = [拼接字符串],前缀: "你好, ",后缀: "世界"

# 只传递必要参数，使用默认值
简单问候 = [拼接字符串],前缀: "你好"
[打印],内容: ${简单问候}  # 输出: 你好默认后缀
```

### 4. API测试入门

#### 简单的GET请求

```python
@name: "API测试入门"
@description: "学习基本的API测试方法"

# 简单的GET请求
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.title", "contains", "sunt"]
''', 步骤名称: "获取文章详情"
```

#### 带参数的请求

```python
# 带查询参数的GET请求
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            userId: 1
            _limit: 5
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "length", "eq", 5]
''', 步骤名称: "获取用户文章列表"
```

#### 数据捕获和变量使用

```python
# 捕获响应数据
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/1
    captures:
        user_name: ["jsonpath", "$.name"]
        user_email: ["jsonpath", "$.email"]
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "获取用户信息"

# 使用捕获的变量
[打印], 内容: "用户名: ${user_name}"
[打印], 内容: "邮箱: ${user_email}"

# 在后续请求中使用
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            userId: 1
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "根据用户ID获取文章"
```

## 🚀 进阶功能

### 1. 环境配置管理

#### YAML变量文件

创建 `config/dev.yaml` 管理开发环境配置：

```yaml
# 环境配置
environment: "development"
debug: true

# API配置
api:
  base_url: "https://jsonplaceholder.typicode.com"
  timeout: 30
  retry_count: 3

# HTTP客户端配置
http_clients:
  default:
    base_url: "${api.base_url}"
    timeout: ${api.timeout}
    headers:
      Content-Type: "application/json"
      User-Agent: "pytest-dsl/1.0"

# 测试数据
test_users:
  admin:
    username: "admin"
    password: "admin123"
  normal:
    username: "user"
    password: "user123"

# 数据库配置
database:
  host: "localhost"
  port: 5432
  name: "test_db"
```

#### 使用配置文件

```bash
# 运行时指定配置文件
pytest-dsl tests/ --yaml-vars config/dev.yaml
```

#### 在DSL中使用配置

```python
@name: "使用环境配置"

# 直接使用YAML中的变量
[打印], 内容: "当前环境: ${environment}"
[打印], 内容: "API地址: ${api.base_url}"

# 使用嵌套配置（支持增强的变量访问语法）
admin_user = ${test_users.admin.username}
admin_pass = ${test_users.admin.password}

# 支持数组索引访问
first_user = ${users_array[0].name}
last_user = ${users_array[-1].name}

# 支持字典键访问
api_server = ${config_map["api-server"]}
timeout_config = ${config_map['timeout']}

[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: ${api.base_url}/auth/login
    request:
        json:
            username: "${admin_user}"
            password: "${admin_pass}"
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "管理员登录"
```

### 2. 增强的变量访问语法

pytest-dsl 支持类似 Python 的强大变量访问语法：

#### 支持的语法类型

```python
# 基本变量访问
${variable_name}

# 点号访问（对象属性）
${object.property}
${nested.object.property}

# 数组索引访问
${array[0]}          # 第一个元素
${array[-1]}         # 最后一个元素

# 字典键访问
${dict["key"]}       # 使用双引号
${dict['key']}       # 使用单引号

# 混合访问模式
${users[0].name}                    # 数组中对象的属性
${data["users"][0]["name"]}         # 嵌套字典和数组
${config.servers[0].endpoints["api"]} # 复杂嵌套结构
```

#### 实际使用示例

```yaml
# YAML配置文件
users:
  - id: 1
    name: "张三"
    roles: ["admin", "user"]
    profile:
      email: "zhangsan@example.com"
      settings:
        theme: "dark"

config:
  "api-server": "https://api.example.com"
  "timeout": 30
```

```python
# DSL测试文件
@name: "变量访问语法示例"

# 数组访问
first_user = ${users[0].name}
[打印], 内容: "第一个用户: ${first_user}"

# 嵌套访问
user_theme = ${users[0].profile.settings.theme}
[打印], 内容: "用户主题: ${user_theme}"

# 字典键访问
api_server = ${config["api-server"]}
[打印], 内容: "API服务器: ${api_server}"

# 在字符串中使用
[打印], 内容: "用户${users[0].name}的角色是${users[0].roles[0]}"
```

详细文档请参考：[增强的变量访问语法](docs/enhanced_variable_access.md)

### 3. 数据驱动测试

#### CSV数据驱动

注意：这种数据驱动模式只有用pytest命令运行的时候才可以

创建 `test_data.csv`：

```csv
username,password,expected_status,test_case
admin,admin123,200,管理员登录成功
user,user123,200,普通用户登录成功
invalid,wrong,401,错误密码登录失败
"",admin123,400,空用户名登录失败
```

使用CSV数据：

```python
@name: "登录功能测试"
@data: "test_data.csv" using csv
@description: "使用CSV数据测试登录功能"

# CSV中的每一行都会执行一次这个测试
[打印], 内容: "测试用例: ${test_case}"
[打印], 内容: "用户名: ${username}, 密码: ${password}, 期望状态: ${expected_status}"

# 模拟HTTP请求（实际应该是真实的API调用）
[打印], 内容: "模拟登录请求..."

# 简单的条件判断来模拟不同的测试结果
if "${username}" == "admin" do
    [打印], 内容: "管理员登录测试"
else
    [打印], 内容: "无效用户登录测试"
end

[打印], 内容: "测试用例: ${test_case} - 完成"
```

### 3. 断言重试机制

对于异步API或需要等待的场景：

```python
# 带重试的断言
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 1]
''', 断言重试次数: 3, 断言重试间隔: 1, 步骤名称: "测试断言重试机制"
```

### 4. 远程关键字功能

pytest-dsl支持分布式测试，可以在不同机器上执行关键字：

#### 启动远程服务

```bash
# 在远程机器上启动关键字服务
pytest-dsl-server --host 0.0.0.0 --port 8270

# 带API密钥的安全启动
pytest-dsl-server --host 0.0.0.0 --port 8270 --api-key your_secret_key

# 控制最大并发请求数（默认20）
pytest-dsl-server --host 0.0.0.0 --port 8270 --max-concurrency 50
```

#### 使用远程关键字

**方式一：DSL中直接连接**

```python
@name: "远程关键字测试"
@remote: "http://remote-server:8270/" as remote_machine

# 在远程机器上执行关键字
remote_machine|[打印], 内容: "这在远程机器上执行"
result = remote_machine|[生成随机数], 最小值: 1, 最大值: 100
[打印], 内容: "远程生成的随机数: ${result}"
```

**方式二：YAML配置自动加载（推荐）**

在 `config/vars.yaml` 中配置：

```yaml
remote_servers:
  main_server:
    url: "http://server1:8270/"
    alias: "server1"
    api_key: "your_api_key"
    timeout: 60
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: true

  backup_server:
    url: "http://server2:8270/"
    alias: "server2"
```

然后直接使用：

```python
# 无需@remote导入，直接使用
server1|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
'''

server2|[打印], 内容: "备用服务器执行"
```

#### 无缝变量传递

客户端的变量会自动传递到远程服务器：

```python
# 客户端定义的变量
api_url = "https://jsonplaceholder.typicode.com"
user_token = "abc123"

# 远程服务器可以直接使用这些变量
remote_machine|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_url}/users/1
    request:
        headers:
            Authorization: "Bearer ${user_token}"
'''
```

## 📋 实战案例

### 完整的API测试项目

让我们创建一个完整的API测试项目来演示pytest-dsl的强大功能：

#### 项目结构

```
my-api-tests/
├── config/
│   ├── dev.yaml          # 开发环境配置
│   ├── prod.yaml         # 生产环境配置
│   └── base.yaml         # 基础配置
├── resources/
│   ├── auth.resource     # 认证相关关键字
│   └── utils.resource    # 工具关键字
├── tests/
│   ├── auth/
│   │   ├── login.dsl     # 登录测试
│   │   └── logout.dsl    # 登出测试
│   ├── users/
│   │   ├── create_user.dsl
│   │   └── get_user.dsl
│   └── data/
│       └── users.csv     # 测试数据
├── test_runner.py        # pytest集成
└── pytest.ini           # pytest配置
```

#### 基础配置 `config/base.yaml`

```yaml
# 通用配置
app_name: "My API"
version: "1.0.0"

# HTTP客户端配置
http_clients:
  default:
    timeout: 30
    headers:
      Content-Type: "application/json"
      User-Agent: "${app_name}/${version}"
```

#### 开发环境配置 `config/dev.yaml`

```yaml
# 继承基础配置
extends: "base.yaml"

# 开发环境特定配置
environment: "development"
debug: true

api:
  base_url: "https://jsonplaceholder.typicode.com"

# 测试用户
test_users:
  admin:
    username: "admin"
    password: "admin123"
  normal:
    username: "testuser"
    password: "test123"

# 数据库配置
database:
  host: "localhost"
  port: 5432
  name: "test_db"
```

#### 认证关键字 `resources/auth.resource`

```python
@name: "认证相关关键字"
@description: "处理登录、登出等认证操作"

function 用户登录 (用户名, 密码, 客户端="default") do
    [打印], 内容: "模拟用户登录: ${用户名}"

    # 模拟HTTP登录请求
    [HTTP请求], 客户端: ${客户端}, 配置: '''
        method: GET
        url: https://jsonplaceholder.typicode.com/users/1
        captures:
            access_token: ["jsonpath", "$.id"]
            user_id: ["jsonpath", "$.id"]
        asserts:
            - ["status", "eq", 200]
    ''', 步骤名称: "用户登录: ${用户名}"

    # 设置全局token供后续请求使用
    [设置全局变量], 变量名: "auth_token", 值: ${access_token}
    [设置全局变量], 变量名: "current_user_id", 值: ${user_id}

    return ${access_token}
end

function 用户登出 (客户端="default") do
    token = [获取全局变量], 变量名: "auth_token"
    [打印], 内容: "模拟用户登出，token: ${token['result']}"

    # 模拟HTTP登出请求
    [HTTP请求], 客户端: ${客户端}, 配置: '''
        method: GET
        url: https://jsonplaceholder.typicode.com/posts/1
        asserts:
            - ["status", "eq", 200]
    ''', 步骤名称: "用户登出"

    # 清除认证信息
    [设置全局变量], 变量名: "auth_token", 值: ""
    [设置全局变量], 变量名: "current_user_id", 值: ""
end
```

#### 登录测试 `tests/auth/login.dsl`

```python
@name: "用户登录功能测试"
@description: "测试用户登录的各种场景"
@tags: ["auth", "login"]
@import: "resources/auth.resource"

# 测试管理员登录
admin_token = [用户登录], 用户名: ${test_users.admin.username}, 密码: ${test_users.admin.password}
[断言], 条件: "${admin_token} != ''", 消息: "管理员登录失败"

# 验证登录状态（模拟）
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.name", "exists"]
''', 步骤名称: "验证登录状态"

# 测试登出
[用户登出]

teardown do
    [打印], 内容: "登录测试完成"
end
```

#### pytest集成 `test_runner.py`

```python
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./tests")
class TestAPI:
    """API自动化测试套件

    自动加载tests目录下的所有DSL文件
    """
    pass

@auto_dsl("./tests/auth")
class TestAuth:
    """认证模块测试"""
    pass

@auto_dsl("./tests/users")
class TestUsers:
    """用户模块测试"""
    pass
```

#### 运行测试

```bash
# 使用开发环境配置运行所有测试
pytest-dsl tests/ --yaml-vars config/dev.yaml

# 使用pytest运行（支持更多选项）
pytest test_runner.py --yaml-vars config/dev.yaml -v

# 生成Allure报告
pytest test_runner.py --yaml-vars config/dev.yaml --alluredir=reports
allure serve reports
```

## 🔧 扩展开发

### 创建自定义关键字

pytest-dsl的强大之处在于可以轻松扩展自定义关键字：

#### 基础关键字开发

```python
# keywords/my_keywords.py
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('数据库查询', [
    {'name': '查询语句', 'mapping': 'sql', 'description': 'SQL查询语句'},
    {'name': '数据库', 'mapping': 'database', 'description': '数据库连接名', 'default': 'default'}
], returns={'type': 'list[dict]', 'description': '查询结果列表'})
def database_query(**kwargs):
    """执行数据库查询"""
    sql = kwargs.get('sql')
    database = kwargs.get('database', 'default')
    context = kwargs.get('context')

    # 从上下文获取数据库配置
    db_config = context.get_variable('database')

    # 实现数据库查询逻辑
    # connection = create_connection(db_config)
    # result = connection.execute(sql)

    # 模拟查询结果
    result = [{"id": 1, "name": "test"}]

    return result

@keyword_manager.register('发送邮件', [
    {'name': '收件人', 'mapping': 'to_email', 'description': '收件人邮箱'},
    {'name': '主题', 'mapping': 'subject', 'description': '邮件主题', 'default': '测试邮件'},
    {'name': '内容', 'mapping': 'content', 'description': '邮件内容', 'default': '这是一封测试邮件'},
    {'name': '优先级', 'mapping': 'priority', 'description': '邮件优先级', 'default': 'normal'}
], returns='bool')
def send_email(**kwargs):
    """发送邮件通知"""
    to_email = kwargs.get('to_email')
    subject = kwargs.get('subject', '测试邮件')
    content = kwargs.get('content', '这是一封测试邮件')
    priority = kwargs.get('priority', 'normal')

    # 实现邮件发送逻辑
    print(f"发送邮件到 {to_email}: {subject} (优先级: {priority})")

    return True
```

#### 在DSL中使用自定义关键字

```python
@name: "使用自定义关键字测试"

# 使用数据库查询关键字
users = [数据库查询], 查询语句: "SELECT * FROM users WHERE active = 1"
[打印], 内容: "查询到 ${len(users)} 个活跃用户"

# 发送测试报告邮件 - 使用默认值
[发送邮件], 收件人: "admin@example.com"  # 主题和内容使用默认值

# 发送自定义邮件 - 覆盖默认值
[发送邮件], 收件人: "dev@example.com", 主题: "部署完成", 内容: "系统已成功部署到生产环境"
```

### 5. 参数默认值功能 🆕

pytest-dsl 现在支持为关键字参数设置默认值，让DSL编写更加简洁：

#### 定义带默认值的关键字

```python
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('HTTP请求', [
    {'name': '地址', 'mapping': 'url', 'description': '请求地址'},
    {'name': '方法', 'mapping': 'method', 'description': 'HTTP方法', 'default': 'GET'},
    {'name': '超时', 'mapping': 'timeout', 'description': '超时时间（秒）', 'default': 30},
    {'name': '重试次数', 'mapping': 'retries', 'description': '重试次数', 'default': 3},
    {'name': '验证SSL', 'mapping': 'verify_ssl', 'description': '是否验证SSL证书', 'default': True}
])
def http_request(**kwargs):
    """HTTP请求关键字，支持默认值"""
    url = kwargs.get('url')
    method = kwargs.get('method', 'GET')  # 默认值也会自动应用
    timeout = kwargs.get('timeout', 30)
    retries = kwargs.get('retries', 3)
    verify_ssl = kwargs.get('verify_ssl', True)
    
    # 执行HTTP请求逻辑
    return {"status": "success", "method": method, "url": url}
```

#### 返回值元数据

建议为 Python 自定义关键字显式声明 `returns`，这样 `list_keywords`、HTML 文档和远程关键字同步都能稳定拿到返回类型，而不必依赖 docstring 的 `Returns:` 文本推断。

```python
@keyword_manager.register(
    '生成Token',
    [
        {'name': '用户ID', 'mapping': 'user_id', 'description': '用户标识'}
    ],
    returns={'type': 'str', 'description': '生成后的访问令牌'}
)
def generate_token(**kwargs):
    return 'token-123'
```

支持两种写法：

- `returns='str'`
- `returns={'type': 'list[dict]', 'description': '查询结果列表'}`

如果没有显式写 `returns`，pytest-dsl 会按“函数返回注解 -> docstring 的 `Returns:` -> 无返回元数据”的顺序尝试推断。

#### 在DSL中使用默认值

```python
@name: "默认值功能演示"

# 只传递必需参数，其他使用默认值
response1 = [HTTP请求], 地址: "https://api.example.com/users"
# 等价于：方法: "GET", 超时: 30, 重试次数: 3, 验证SSL: True

# 部分覆盖默认值
response2 = [HTTP请求], 地址: "https://api.example.com/users", 方法: "POST", 超时: 60
# 只覆盖方法和超时，重试次数和SSL验证仍使用默认值

# 内置关键字也支持默认值
random_num = [生成随机数]  # 使用默认范围 0-100，整数
custom_num = [生成随机数], 最大值: 50  # 只修改最大值，其他保持默认

# 生成随机字符串
default_string = [生成随机字符串]  # 长度8，字母数字混合
custom_string = [生成随机字符串], 长度: 12, 类型: "letters"  # 自定义长度和类型
```

#### 默认值的优势

- **🎯 简化调用** - 只需传递关键参数，常用配置自动应用
- **🔧 灵活覆盖** - 可选择性地覆盖任何默认值
- **📖 提高可读性** - DSL更加简洁，重点突出
- **🛡️ 减少错误** - 避免重复配置常用参数
- **🌐 远程支持** - 远程关键字也完整支持默认值功能

#### 支持远程模式的关键字

```python
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('文件操作', [
    {'name': '操作类型', 'mapping': 'operation', 'description': '操作类型：read/write/delete'},
    {'name': '文件路径', 'mapping': 'file_path', 'description': '文件路径'},
    {'name': '内容', 'mapping': 'content', 'description': '文件内容（写入时使用）', 'default': ''}
])
def file_operation(**kwargs):
    """文件操作关键字，支持远程执行"""
    operation = kwargs.get('operation')
    file_path = kwargs.get('file_path')
    content = kwargs.get('content', '')

    if operation == 'read':
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    elif operation == 'write':
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    elif operation == 'delete':
        # 删除文件
        import os
        os.remove(file_path)
        return True

    return False
```

### 关键字开发最佳实践

1. **参数验证**：始终验证输入参数
2. **错误处理**：提供清晰的错误信息
3. **文档说明**：为每个关键字提供详细的文档
4. **返回值**：确保关键字有明确的返回值
5. **上下文使用**：合理使用context获取全局变量

## 🚀 部署运维

### 与pytest集成

```python
# test_runner.py
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./tests")
class TestAPI:
    """自动加载tests目录下的所有DSL文件"""
    pass
```

### 生成测试报告

```bash
# 生成Allure报告
pytest test_runner.py --alluredir=reports
allure serve reports

# 生成HTML报告
pytest test_runner.py --html=report.html --self-contained-html
```

### CI/CD集成

#### GitHub Actions示例

```yaml
# .github/workflows/test.yml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install pytest-dsl allure-pytest

    - name: Run tests
      run: |
        pytest test_runner.py --alluredir=allure-results

    - name: Generate report
      uses: simple-elf/allure-report-action@master
      if: always()
      with:
        allure_results: allure-results
        allure_history: allure-history
```

### Docker部署

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["pytest-dsl", "tests/", "--yaml-vars", "config/prod.yaml"]
```

## 📖 参考文档

### 核心功能文档
- [完整DSL语法指南](./docs/自动化关键字DSL语法设计.md)
- [HTTP测试关键字详解](./docs/api.md)
- [断言关键字使用指南](./docs/assertion_keywords.md)
- [HTTP断言重试机制](./docs/http_assertion_retry.md)

### 自定义关键字文档
- 🎯 [自定义关键字概览](./docs/guide/custom-keywords.md)
- 🚀 [Python代码自定义关键字](./docs/guide/custom-keywords-python.md)
- 🔄 [关键字远程与本地适配指南](./docs/guide/keyword-remote-local-adaptation.md)

### 远程关键字文档
- 📖 [远程关键字使用指南](./docs/remote-keywords-usage.md)
- 🛠️ [远程关键字开发指南](./docs/remote-keywords-development.md)
- 🔧 [远程服务器Hook机制](./docs/remote-hooks-guide.md)
- ⚙️ [YAML远程服务器配置](./docs/yaml_remote_servers.md)
- 🔄 [变量无缝传递功能](./docs/yaml_vars_seamless_sync.md)

### 示例和最佳实践
- [远程关键字验证示例](./examples/remote/)
- [配置文件示例](./examples/config/)

## 🎯 为什么选择pytest-dsl？

### 核心优势

- **🎯 零门槛上手** - 自然语言风格，测试人员无需编程基础
- **🔧 高度可扩展** - 轻松创建自定义关键字，适应任何测试场景
- **🌐 分布式支持** - 内置远程关键字功能，支持大规模分布式测试
- **🔄 无缝集成** - 完美兼容pytest生态，可渐进式迁移
- **📊 丰富报告** - 集成Allure，提供专业级测试报告
- **🛡️ 企业级特性** - 支持环境隔离、变量管理、安全认证

### 适用场景

- **API接口测试** - 完整的HTTP测试支持
- **分布式测试** - 跨服务调用、服务间通信和分布式系统测试
- **回归测试** - 数据驱动和批量执行
- **集成测试** - 跨系统测试协调
- **性能测试** - 结合其他工具进行性能测试

## 📋 示例验证

本README.md中的大部分示例都已经过验证，确保可以正常运行。验证示例位于 `examples/readme_validation/` 目录中。

### 运行验证

```bash
# 进入验证目录
cd examples/readme_validation

# 运行所有验证示例
python run_all_tests.py

# 或者运行单个示例
pytest-dsl hello.dsl
pytest-dsl api_basic.dsl
```

### 验证覆盖

- ✅ 基础语法和内置关键字
- ✅ 自定义关键字和资源文件
- ✅ API测试功能
- ✅ YAML配置管理
- ✅ 变量访问语法
- ✅ 断言重试机制
- ✅ 认证功能示例
- ✅ 数据驱动测试（pytest集成）
- ✅ 布尔值支持和条件判断
- ✅ 字典定义和嵌套访问
- ✅ 循环控制语句（break/continue）

---

🚀 **开始使用pytest-dsl，让测试自动化变得简单而强大！**


## 🤝 贡献与支持

我们欢迎您的贡献和反馈！

- 🐛 [报告问题](https://github.com/felix-1991/pytest-dsl/issues)
- 💡 [功能建议](https://github.com/felix-1991/pytest-dsl/discussions)
- 🔧 [提交PR](https://github.com/felix-1991/pytest-dsl/pulls)

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---
