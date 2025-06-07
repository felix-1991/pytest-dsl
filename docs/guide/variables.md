# 变量和数据类型

变量是pytest-dsl中的核心概念，用于存储和传递数据。本章将详细介绍如何定义、使用和管理变量。

## 变量定义

### 基本语法

```python
# 字符串变量
name = "pytest-dsl"
message = "Hello, World!"

# 数字变量
age = 25
price = 99.99
count = 0

# 布尔变量
is_enabled = True
is_debug = False
```

### 变量命名规则

- 变量名必须以字母或下划线开头
- 可以包含字母、数字和下划线
- 区分大小写
- 不能使用Python关键字

```python
# 正确的变量名
user_name = "张三"
api_url = "https://api.example.com"
test_count = 10
_private_var = "私有变量"

# 错误的变量名（避免使用）
# 2user = "错误"      # 不能以数字开头
# user-name = "错误"  # 不能包含连字符
# class = "错误"      # 不能使用关键字
```

## 数据类型

### 字符串 (String)

```python
# 单引号字符串
name = 'pytest-dsl'

# 双引号字符串
description = "强大的测试框架"

# 多行字符串
long_text = '''
这是一个
多行字符串
示例
'''

# 字符串拼接
first_name = "张"
last_name = "三"
full_name = first_name + last_name

# 字符串格式化
user_id = 123
message = f"用户ID: {user_id}"
```

### 数字 (Number)

```python
# 整数
count = 42
negative = -10
zero = 0

# 浮点数
price = 99.99
rate = 0.85
scientific = 1.23e-4

# 数学运算
sum_result = 10 + 5      # 15
diff_result = 10 - 3     # 7
mult_result = 4 * 6      # 24
div_result = 15 / 3      # 5.0
mod_result = 17 % 5      # 2
power_result = 2 ** 3    # 8
```

### 布尔值 (Boolean)

```python
# 布尔字面量
is_active = True
is_disabled = False

# 布尔运算
result1 = True and False    # False
result2 = True or False     # True
result3 = not True          # False

# 比较运算产生布尔值
is_equal = (5 == 5)         # True
is_greater = (10 > 5)       # True
is_less = (3 < 2)           # False
```

### 列表 (List)

```python
# 空列表
empty_list = []

# 数字列表
numbers = [1, 2, 3, 4, 5]

# 字符串列表
names = ["张三", "李四", "王五"]

# 混合类型列表
mixed = [1, "hello", True, 3.14]

# 嵌套列表
matrix = [[1, 2], [3, 4], [5, 6]]

# 列表操作
first_item = numbers[0]      # 1
last_item = numbers[-1]      # 5
# list_length = len(numbers)   # 不支持：函数调用
# 需要预定义数组长度或使用其他方式获取长度
list_length = 5              # 手动指定长度
```

### 字典 (Dictionary)

```python
# 空字典
empty_dict = {}

# 用户信息字典
user = {
    "id": 1,
    "name": "张三",
    "age": 30,
    "email": "zhangsan@example.com"
}

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

# 字典访问
user_name = user["name"]
db_host = config["database"]["host"]
```

## 变量引用

### 基本引用语法

```python
# 定义变量
username = "admin"
password = "123456"

# 在关键字中使用变量
[打印], 内容: ${username}
[打印], 内容: "用户名: ${username}, 密码: ${password}"
```

### 增强的变量访问语法

pytest-dsl支持类似Python的强大变量访问语法：

```python
# 点号访问（对象属性）
user_name = ${user.name}
db_host = ${config.database.host}

# 数组索引访问
first_user = ${users[0]}
last_user = ${users[-1]}

# 字典键访问
api_server = ${config["api-server"]}
timeout_config = ${config['timeout']}

# 混合访问模式
first_user_name = ${users[0].name}
api_endpoint = ${config.servers[0].endpoints["api"]}
```

### 在字符串中使用变量

```python
# 字符串插值
name = "pytest-dsl"
version = "1.0.0"
message = "欢迎使用 ${name} ${version}!"

# 复杂表达式
user_count = 100
status_message = "系统中有 ${user_count} 个用户"

# 在HTTP请求中使用
api_base = "https://api.example.com"
user_id = 123
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_base}/users/${user_id}
'''
```

## 变量作用域

### 局部变量

```python
# 在测试文件中定义的变量是局部变量
local_var = "这是局部变量"

# 在函数中定义的变量也是局部的
function 测试函数 () do
    function_var = "函数内变量"
    [打印], 内容: ${function_var}
end
```

### 全局变量

```python
# 设置全局变量
[设置全局变量], 变量名: "global_config", 值: "全局配置"

# 获取全局变量
config_value = [获取全局变量], 变量名: "global_config"
[打印], 内容: ${config_value}

# 在不同测试文件间共享
[设置全局变量], 变量名: "shared_token", 值: "abc123"
```

### YAML配置变量

```yaml
# config/vars.yaml
app:
  name: "My App"
  version: "1.0.0"

database:
  host: "localhost"
  port: 3306
```

```python
# 在DSL中使用YAML变量
app_name = ${app.name}
db_port = ${database.port}

[打印], 内容: "应用: ${app_name}, 数据库端口: ${db_port}"
```

## 变量操作

### 变量赋值

```python
# 直接赋值
name = "张三"

# 从关键字返回值赋值
random_num = [生成随机数], 最小值: 1, 最大值: 100

# 从HTTP响应捕获
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/user/1
    captures:
        user_id: ["jsonpath", "$.id"]
        user_name: ["jsonpath", "$.name"]
'''

# 使用捕获的变量
[打印], 内容: "用户ID: ${user_id}, 姓名: ${user_name}"
```

### 变量计算

```python
# 数学计算
a = 10
b = 5
sum_result = a + b
product = a * b

# 字符串操作
first_name = "张"
last_name = "三"
full_name = first_name + last_name

# 列表操作
numbers = [1, 2, 3]
first_number = numbers[0]
# list_size = len(numbers)  # 不支持：函数调用
list_size = 3  # 手动指定长度
```

### 条件赋值

```python
# 根据条件赋值变量
environment = "development"

if environment == "development" do
    api_url = "https://dev-api.example.com"
    debug_mode = True
else
    api_url = "https://api.example.com"
    debug_mode = False
end

[打印], 内容: "API地址: ${api_url}, 调试模式: ${debug_mode}"
```

## 数据类型转换

### 类型转换限制

```python
# 注意：当前不支持直接的类型转换函数调用
# number_val = int(number_str)    # 不支持
# float_val = float(float_str)    # 不支持
# bool_val = bool(bool_str)       # 不支持

# 需要手动指定类型或使用其他方式
number_str = "123"
number_val = 123    # 直接赋值为数字类型

float_str = "3.14"
float_val = 3.14    # 直接赋值为浮点类型

bool_str = "True"
bool_val = True     # 直接赋值为布尔类型
```

### 类型检查

```python
# 使用类型断言检查变量类型
name = "pytest-dsl"
age = 25
is_active = True

[类型断言], 值: ${name}, 类型: "string", 消息: "name应该是字符串"
[类型断言], 值: ${age}, 类型: "number", 消息: "age应该是数字"
[类型断言], 值: ${is_active}, 类型: "boolean", 消息: "is_active应该是布尔值"
```

## 复杂数据结构

### 处理JSON数据

```python
# JSON字符串
json_str = '{"name": "张三", "age": 30, "skills": ["Python", "Java"]}'

# 从JSON提取数据
user_name = [JSON提取], JSON数据: ${json_str}, JSONPath: "$.name"
user_age = [JSON提取], JSON数据: ${json_str}, JSONPath: "$.age"
first_skill = [JSON提取], JSON数据: ${json_str}, JSONPath: "$.skills[0]"

[打印], 内容: "姓名: ${user_name}, 年龄: ${user_age}, 技能: ${first_skill}"
```

### 处理嵌套结构

```python
# 复杂的嵌套数据
company_data = {
    "name": "科技公司",
    "departments": [
        {
            "name": "开发部",
            "employees": [
                {"name": "张三", "role": "工程师"},
                {"name": "李四", "role": "架构师"}
            ]
        },
        {
            "name": "测试部",
            "employees": [
                {"name": "王五", "role": "测试工程师"}
            ]
        }
    ]
}

# 访问嵌套数据
company_name = ${company_data.name}
first_dept = ${company_data.departments[0].name}
first_employee = ${company_data.departments[0].employees[0].name}

[打印], 内容: "公司: ${company_name}"
[打印], 内容: "第一个部门: ${first_dept}"
[打印], 内容: "第一个员工: ${first_employee}"
```

## 变量最佳实践

### 1. 命名约定

```python
# 使用有意义的变量名
user_id = 123                    # 好
u = 123                         # 不好

# 使用下划线分隔单词
api_base_url = "https://api.example.com"    # 好
apibaseurl = "https://api.example.com"      # 不好

# 布尔变量使用is_前缀
is_enabled = True               # 好
enabled = True                  # 可以，但不如上面清晰
```

### 2. 变量初始化

```python
# 在使用前初始化变量
user_token = ""
user_id = 0
is_logged_in = False

# 使用默认值
api_timeout = 30
max_retries = 3
```

### 3. 变量分组

```python
# 相关变量分组定义
# API配置
api_base_url = "https://api.example.com"
api_timeout = 30
api_version = "v1"

# 用户数据
user_name = "admin"
user_password = "123456"
user_role = "administrator"

# 测试配置
test_environment = "development"
debug_mode = True
log_level = "INFO"
```

### 4. 使用配置文件

```yaml
# config/test.yaml
api:
  base_url: "https://api.example.com"
  timeout: 30
  version: "v1"

users:
  admin:
    username: "admin"
    password: "admin123"
  normal:
    username: "user"
    password: "user123"
```

```python
# 在DSL中使用配置
api_url = ${api.base_url}
admin_user = ${users.admin.username}
admin_pass = ${users.admin.password}
```

## 常见问题

### 1. 变量未定义错误

```python
# 错误：使用未定义的变量
[打印], 内容: ${undefined_var}  # 会报错

# 正确：先定义再使用
undefined_var = "现在已定义"
[打印], 内容: ${undefined_var}
```

### 2. 变量类型错误

```python
# 错误：类型不匹配
number_var = "123"  # 字符串
result = number_var + 10  # 错误：字符串不能直接与数字相加

# 正确：类型转换
number_var = "123"
result = int(number_var) + 10  # 正确
```

### 3. 变量作用域问题

```python
# 在函数外定义
global_var = "全局变量"

function 测试函数 () do
    # 在函数内可以访问外部变量
    [打印], 内容: ${global_var}
    
    # 函数内定义的变量在外部不可访问
    local_var = "局部变量"
end

# 这里无法访问local_var
# [打印], 内容: ${local_var}  # 会报错
```

## 调试技巧

### 1. 打印变量值

```python
# 调试变量值
user_data = {"name": "张三", "age": 30}
[打印], 内容: "用户数据: ${user_data}"

# 打印变量类型 - 注意：当前不支持 type() 函数调用
# [打印], 内容: "变量类型: ${type(user_data)}"  # 不支持
[打印], 内容: "变量类型: 字典"  # 手动指定类型
```

### 2. 条件调试

```python
# 只在调试模式下打印
debug_mode = True

if ${debug_mode} do
    [打印], 内容: "调试信息: user_id = ${user_id}"
    [打印], 内容: "调试信息: api_url = ${api_url}"
end
```

### 3. 变量验证

```python
# 验证变量是否符合预期
user_id = 123
[断言], 条件: "${user_id} > 0", 消息: "用户ID应该大于0"
[断言], 条件: 'isinstance(${user_id}, int)', 消息: "用户ID应该是整数"
```

## 下一步

现在您已经掌握了pytest-dsl中变量和数据类型的使用，可以继续学习：

1. **[流程控制](./control-flow)** - 学习条件判断和循环
2. **[内置关键字](./builtin-keywords)** - 了解框架提供的功能
3. **[自定义关键字](./custom-keywords)** - 创建可复用的测试组件
4. **[HTTP API测试](./http-testing)** - 在API测试中应用变量 