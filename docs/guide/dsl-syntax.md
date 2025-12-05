# DSL语法基础

pytest-dsl使用自然语言风格的领域特定语言(DSL)来编写测试用例。本章将详细介绍DSL的语法规则和使用方法。

## 文件结构

一个完整的DSL文件通常包含以下部分：

```python
# 1. 元信息描述
@name: "测试用例名称"
@description: "测试用例描述"
@tags: ["tag1", "tag2"]

# 2. 资源导入（可选）
@import: "path/to/resource.resource"

# 3. 变量定义
variable_name = "value"

# 4. 自定义关键字定义（可选）
function 关键字名称 (参数1, 参数2="默认值") do
    # 关键字实现
end

# 5. 测试主体
[关键字调用], 参数: 值

# 6. 清理操作（可选）
teardown do
    # 清理代码
end
```

## 元信息标签

元信息标签以`@`开头，用于描述测试用例的基本信息：

### 基本标签

```python
@name: "用户登录测试"                    # 测试用例名称（必需）
@description: "测试用户登录功能的各种场景"   # 测试用例描述
@tags: ["login", "smoke", "api"]        # 标签列表
@author: "张三"                         # 编写人
@date: "2024-01-15"                    # 创建日期
```

`@date`支持`YYYY-MM-DD`或`YYYY-MM-DD HH:MM:SS`格式的日期字面量，也可以写成普通字符串。

### 数据驱动标签

```python
@data: "test_data.csv" using csv        # CSV数据驱动
@data: "test_data.json" using json      # JSON数据驱动
```

`using`后跟数据格式标识符（不需要引号），如`csv`、`json`。

### 资源导入标签

```python
@import: "common/auth.resource"         # 导入资源文件
@import: "utils/helpers.resource"       # 可以导入多个资源文件
```

### 远程服务器标签

```python
@remote: "http://server:8270/" as server1   # 声明远程关键字源并指定别名
# 同一文件可声明多个远程源，别名必须唯一
```

## 变量系统

### 基本变量类型

```python
# 字符串
name = "pytest-dsl"
message = "Hello, World!"

# 数字
port = 8080
version = 1.0
count = 5

# 布尔值
is_enabled = True
is_debug = False

# 列表
tags = ["api", "test", "automation"]
numbers = [1, 2, 3, 4, 5]

# 字典
user = {
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
```

### 变量引用

使用`${变量名}`语法引用变量：

```python
name = "pytest-dsl"
version = "1.0"

# 基本引用
[打印], 内容: "项目名称: ${name}"
[打印], 内容: "版本: ${version}"

# 字符串拼接
full_name = "${name}-${version}"

# 字典访问
user = {"name": "张三", "age": 30}
[打印], 内容: "用户名: ${user['name']}"

# 嵌套访问
config = {"db": {"host": "localhost"}}
[打印], 内容: "数据库地址: ${config['db']['host']}"
```

### 增强的变量访问语法

pytest-dsl支持类似Python的强大变量访问语法：

```python
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

### 全局变量

全局变量可以在不同测试用例之间共享：

```python
# 方式1：使用g_前缀
g_username = "admin"
g_token = "abc123"

# 方式2：使用关键字
[设置全局变量], 变量名: "session_id", 值: "xyz789"
session_id = [获取全局变量], 变量名: "session_id"
```

## 流程控制

### 条件判断

```python
# 基本if语句
status = "success"
if status == "success" do
    [打印], 内容: "测试通过"
else
    [打印], 内容: "测试失败"
end

# 多分支和逻辑运算
count = 5
is_retry = False
if ${count} > 10 and not ${is_retry} do
    [打印], 内容: "数量大于10且不是重试"
elif ${count} in [5, 6, 7] do
    [打印], 内容: "数量在允许范围: ${count}"
elif ${count} == 3 do
    [打印], 内容: "数量等于3"
else
    [打印], 内容: "数量其他情况"
end

# 成员判断
state = "running"
if ${state} not in ["failed", "aborted"] do
    [打印], 内容: "状态正常: ${state}"
end

# 嵌套判断
is_ready = True
if ${is_ready} do
    if ${count} >= 5 do
        [打印], 内容: "就绪且数量满足: ${count}"
    end
end
```

### 循环结构

```python
# 数字范围循环
for i in range(1, 5) do
    [打印], 内容: "循环次数: ${i}"
end

# 范围可以是表达式
start = 2
finish = 6
for i in range(${start}, ${finish}) do
    [打印], 内容: "当前: ${i}"
end

# 列表遍历循环（普通列表或数据驱动列表均可）
items = ["apple", "banana", "orange"]
for item in items do
    [打印], 内容: "当前项: ${item}"
end

# 字典列表循环
users = [
    {"name": "张三", "age": 25},
    {"name": "李四", "age": 30}
]
for user in users do
    [打印], 内容: "用户: ${user['name']}, 年龄: ${user['age']}"
end

# 键值对遍历
user_profile = {"name": "王五", "age": 28}
for key, value in user_profile do
    [打印], 内容: "${key}: ${value}"
end

# 嵌套循环
matrix = [
    [1, 2],
    [3, 4]
]
for row in matrix do
    for col in row do
        [打印], 内容: "元素: ${col}"
    end
end
```

> 占位符支持属性、列表索引和字典键混合访问（如`${users[0]['name']}`），使用前请确保对应数据结构已初始化。

### 循环控制

```python
# break和continue
for i in range(1, 11) do
    # 跳过偶数
    if ${i} % 2 == 0 do
        continue
    end

    # 当达到7时退出循环
    if ${i} == 7 do
        [打印], 内容: "达到7，退出循环"
        break
    end

    [打印], 内容: "奇数: ${i}"
end
```

## 关键字调用

### 基本语法

关键字调用使用方括号语法：

```python
# 基本调用
[关键字名称], 参数名: 参数值

# 多个参数
[关键字名称], 参数1: 值1, 参数2: 值2, 参数3: 值3

# 带返回值
result = [关键字名称], 参数: 值
```

### 参数类型

```python
# 字符串参数
[打印], 内容: "Hello World"

# 数字参数
[等待], 秒数: 5

# 布尔参数
[断言], 条件: "1 == 1", 消息: "数学错误"

# 变量参数
message = "测试消息"
[打印], 内容: ${message}

# 多行字符串参数（YAML格式）；支持''' '''或\"\"\" \"\"\"包裹
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/users
    asserts:
        - ["status", "eq", 200]
'''
```

### 远程关键字调用

声明了`@remote`后，可用管道语法调用远程关键字：

```python
@remote: "http://server:8270/" as server1

# 无参数
server1 | [健康检查]

# 带参数
结果 = server1 | [登录], 用户名: "admin", 密码: "123456"
```

## 自定义关键字（函数）

### 基本定义

```python
function 关键字名称 (参数1, 参数2="默认值") do
    # 关键字实现
    [打印], 内容: "参数1: ${参数1}, 参数2: ${参数2}"
    
    # 可以有返回值
    result = "处理结果"
    return ${result}
end
```

### 实际示例

```python
# 定义一个计算器关键字
function 计算器 (操作, 数字1, 数字2=0) do
    if ${操作} == "加法" do
        结果 = ${数字1} + ${数字2}
    elif ${操作} == "减法" do
        结果 = ${数字1} - ${数字2}
    else
        结果 = 0
    end

    [打印], 内容: "${数字1} ${操作} ${数字2} = ${结果}"
    return ${结果}
end

# 使用自定义关键字
sum_result = [计算器], 操作: "加法", 数字1: 10, 数字2: 5
diff_result = [计算器], 操作: "减法", 数字1: 10  # 数字2使用默认值0
```

> 参数默认值目前仅支持字符串或数字字面量。

## 资源文件

### 创建资源文件

资源文件使用`.resource`扩展名：

```python
# utils.resource
@name: "通用工具关键字"

function 拼接字符串 (前缀, 后缀="默认后缀") do
    结果 = "${前缀}${后缀}"
    [打印], 内容: "拼接结果: ${结果}"
    return ${结果}
end

function 生成问候语 (姓名) do
    问候语 = "你好, ${姓名}!"
    return ${问候语}
end
```

### 使用资源文件

```python
@name: "使用资源文件示例"
@import: "utils.resource"

# 使用导入的关键字
结果 = [拼接字符串], 前缀: "Hello, ", 后缀: "World!"
问候 = [生成问候语], 姓名: "张三"

[打印], 内容: ${结果}
[打印], 内容: ${问候}
```

## 清理操作

使用`teardown`块定义测试后的清理操作：

```python
@name: "带清理的测试"

# 测试主体
[打印], 内容: "执行测试..."

# 清理操作（无论测试成功还是失败都会执行）
teardown do
    [打印], 内容: "清理临时文件..."
    [设置全局变量], 变量名: "test_status", 值: "completed"
end
```

## 表达式与运算符

在条件、循环、赋值、参数中均可使用表达式，支持以下运算：

- 比较运算：`>` `<` `>=` `<=` `==` `!=`，成员运算：`in`、`not in`
- 逻辑运算：`and`、`or`、`not`
- 算术运算：`+` `-` `*` `/` `%`，括号可调整优先级
- 布尔字面量：`True`、`False`
- 列表/字典字面量：`[1, 2]`、`{"a": 1, "b": 2}`

> 运算符优先级从低到高：`,` < `or` < `and` < `not` < `in/not in` < 比较运算 < 加减 < 乘除模。必要时使用括号明确顺序。

## 注释

DSL支持Python风格的注释：

```python
# 这是单行注释
[打印], 内容: "Hello"  # 行尾注释

# 多行注释可以用多个单行注释
# 第一行注释
# 第二行注释
[打印], 内容: "World"
```

## 语法最佳实践

### 1. 命名规范

```python
# 好的命名
user_name = "张三"
api_base_url = "https://api.example.com"

function 用户登录 (用户名, 密码) do
    # 实现
end

# 避免的命名
x = "张三"
url = "https://api.example.com"

function f (a, b) do
    # 实现
end
```

### 2. 代码组织

```python
# 将相关的变量放在一起
# 用户相关配置
user_name = "admin"
user_password = "admin123"
user_email = "admin@example.com"

# API相关配置
api_base_url = "https://api.example.com"
api_timeout = 30

# 将相关的操作放在一起
# 用户登录流程
[用户登录], 用户名: ${user_name}, 密码: ${user_password}
[验证登录状态]
[获取用户信息]
```

### 3. 错误处理

```python
# 使用断言进行验证
[断言], 条件: "${response_status} == 200", 消息: "API请求失败"

# 使用条件判断处理不同情况
if ${response_status} == 200 do
    [打印], 内容: "请求成功"
else
    [打印], 内容: "请求失败，状态码: ${response_status}"
end
```

## 常见错误

### 1. 变量引用错误

```python
# ❌ 错误：忘记使用${}
name = "test"
[打印], 内容: name  # 这会打印字面量"name"

# ✅ 正确：使用${}引用变量
[打印], 内容: ${name}  # 这会打印"test"
```

### 2. 语法结构错误

```python
# ❌ 错误：忘记end关键字
if condition do
    [打印], 内容: "test"
# 缺少end

# ✅ 正确：完整的语法结构
if condition do
    [打印], 内容: "test"
end
```

### 3. 参数传递错误

```python
# ❌ 错误：参数名不匹配
[HTTP请求], url: "https://api.example.com"  # 应该是"客户端"和"配置"

# ✅ 正确：使用正确的参数名
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com
'''
```

## 下一步

现在您已经掌握了DSL的基本语法，可以继续学习：

- **[变量和数据类型](./variables)** - 深入了解变量系统
- **[流程控制](./control-flow)** - 掌握条件和循环的高级用法
- **[内置关键字](./builtin-keywords)** - 学习框架提供的内置功能 
