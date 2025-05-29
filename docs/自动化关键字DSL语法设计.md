# pytest-dsl 自动化关键字DSL语法设计

## 目的

pytest-dsl是一个基于pytest的关键字驱动测试框架，使用自定义的领域特定语言(DSL)来编写测试用例，使测试更加直观、易读和易维护。本文档详细描述了DSL语法设计和使用方法。

## DSL语法示例

```python
@name: "测试用例示例"
@description: "这是一个测试用例示例，展示DSL语法的主要特性"
@tags: [BVT, 自动化]
@author: Felix
@date: 2024-06-15

# 变量定义
message = "Hello, pytest-dsl!"
number = 5

# 自定义关键字（函数）定义
function 打印消息 (内容) do
    [打印],内容:${内容}
end

# 使用自定义关键字
[打印消息],内容: ${message}

# 循环结构
for i in range(1, ${number}) do
    [打印],内容: "第${i}次循环"
end

# 条件判断
if number > 3 do
    [打印],内容: "number大于3"
else
    [打印],内容: "number不大于3"
end

# 关键字调用示例
[HTTP请求],客户端:"default",配置:'''
    method: GET
    url: https://www.example.com
    request:
        headers:
            Content-Type: application/json
    asserts:
        - ["status", "eq", 200]
'''

# 清理操作
teardown do
    [打印],内容:"测试结束"
end
```

## DSL语法结构

### 元信息描述部分

用于描述测试用例的基本信息，通常以@开头：

```
@name：用例名称
@description：用例描述
@tags：标签（支持多个标签）
@author：编写人
@date：创建日期
@data：数据驱动测试的数据源
```

### 变量声明与使用

变量可以直接赋值，支持字符串、数字、布尔值、列表等类型：

```python
# 基本变量赋值
name = "pytest-dsl"
version = 1.0
is_active = True
tags = ["api", "test"]

# 使用变量
[打印],内容: "名称: ${name}, 版本: ${version}"
```

### 全局变量

以`g_`开头的变量会自动成为全局变量，可以在不同的测试用例之间共享：

```python
g_username = "testuser"  # 全局变量
```

也可以使用全局变量关键字：

```python
[设置全局变量],变量名:"token",值:"abc123"
token = [获取全局变量],变量名:"token"
```

### 条件判断

使用`if...do...else...end`结构进行条件判断：

```python
if condition do
    # 条件为真时执行的代码
else
    # 条件为假时执行的代码
end
```

### 循环结构

使用`for...in range...do`定义循环：

```python
for i in range(1, 5) do
    [打印],内容: "循环次数: ${i}"
end
```

也支持列表循环：

```python
items = ["a", "b", "c"]
for item in items do
    [打印],内容: "当前项: ${item}"
end
```

### 关键字调用

核心测试步骤是通过类似"关键字+参数"形式来描述的：

格式：`[关键字],参数名1:值1,参数名2:值2,...`

示例：

```python
[打印],内容: "Hello, World!"
[HTTP请求],方法:"GET",URL:"https://example.com"
```

### 自定义关键字（函数）

可以在DSL文件中定义自定义关键字，类似于编程语言中的函数：

```python
function 拼接字符串 (前缀, 后缀="默认后缀") do
    结果 = "${前缀}${后缀}"
    [打印],内容: "拼接结果: ${结果}"
    return ${结果}
end

# 使用自定义关键字
结果 = [拼接字符串],前缀:"Hello, ",后缀:"World!"
```

### 资源文件导入

可以从外部资源文件导入自定义关键字：

```python
@import: "path/to/common_utils.resource"

# 使用导入的关键字
结果 = [拼接字符串],前缀:"开始",后缀:"结束"
```

### 收尾清理（Teardown）

使用`teardown`定义测试后的清理操作：

```python
teardown do
    [打印],内容:"测试结束"
    [删除文件],路径:"temp.txt"
end
```

### 数据驱动测试

使用`@data`指令定义数据驱动测试：

```python
@name: "数据驱动测试示例"
@data: "test_data.csv" using csv

# 使用CSV数据中的列
[HTTP请求],客户端:"default",配置:'''
    method: POST
    url: https://example.com/api/login
    request:
        json:
            username: "${username}"
            password: "${password}"
    asserts:
        - ["status", "eq", ${expected_status}]
'''
```

## 内置关键字

### 系统关键字

| 关键字 | 描述 | 参数 |
|-------|------|------|
| 打印 | 输出信息到控制台 | 内容 |
| 等待 | 等待指定的秒数 | 秒数 |
| 等待条件 | 等待条件满足 | 条件, 超时, 间隔, 消息 |
| 断言 | 验证条件是否为真 | 条件, 消息 |
| 生成随机字符串 | 生成随机字符串 | 长度, 类型 |
| 生成随机数 | 生成随机数 | 最小值, 最大值, 小数位数 |
| 获取当前时间 | 获取当前时间 | 格式, 时区 |
| 字符串操作 | 执行字符串操作 | 操作, 字符串, 参数1, 参数2 |

### 全局变量关键字

| 关键字 | 描述 | 参数 |
|-------|------|------|
| 设置全局变量 | 设置全局变量 | 变量名, 值 |
| 获取全局变量 | 获取全局变量 | 变量名 |
| 删除全局变量 | 删除全局变量 | 变量名 |
| 清除所有全局变量 | 清除所有全局变量 | - |

### HTTP关键字

| 关键字 | 描述 | 参数 |
|-------|------|------|
| HTTP请求 | 发送HTTP请求 | 客户端, 配置, 断言重试次数, 断言重试间隔 |

### 等待功能关键字

等待功能是自动化测试中的重要组成部分，pytest-dsl提供了多种等待关键字：

#### 基本等待

```python
# 等待指定秒数
[等待],秒数: 5
```

#### 条件等待

```python
# 等待条件满足，支持超时和重试间隔设置
[等待条件],条件: "${status} == 'completed'",超时: 30,间隔: 2,消息: "状态未变为completed"
```

#### HTTP断言重试

对于异步API或需要一定处理时间的请求，可以使用断言重试功能：

```python
[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://httpbin.org/delay/2
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.args.task_id", "eq", "${task_id}"]
''',断言重试次数: 3,断言重试间隔: 1
```

## DSL语法关键特性

### 动态性

- 使用占位符（如：`${变量名}`）实现动态参数注入，便于复用和灵活性。

### 可读性

- 采用中文关键字（如：`打印`、`HTTP请求`）和参数描述，使得语法更加直观易懂。

### 结构化

- 函数、循环、变量、关键字调用等模块化设计，易于扩展和维护。

### 元信息增强

- 元信息部分提供了额外的上下文（如`标签`、`作者`），便于用例分类和管理。

## 总结的DSL语法元素

| 类型 | 关键字/格式 | 功能 |
|------|------------|------|
| 元信息 | @name, @description 等 | 测试用例的元信息描述 |
| 变量 | 变量名 = 值 | 声明变量并赋值 |
| 条件判断 | if...do...else...end | 条件控制结构 |
| 循环 | for...in range...do | 循环控制结构 |
| 关键字调用 | [关键字],参数:值 | 调用预定义关键字实现特定功能 |
| 自定义关键字 | @keyword 名称 (参数) do | 定义可复用的关键字 |
| 导入 | @import: "路径" | 导入外部资源文件 |
| 清理操作 | teardown do...end | 定义测试结束后的操作 |
| 数据驱动 | @data: "文件" using 格式 | 定义数据驱动测试 |
