# 基本语法示例

本示例展示pytest-dsl的核心语法特性，包括变量定义、数据类型、条件判断和循环结构。

## 学习目标

- 掌握变量定义和使用
- 了解支持的数据类型
- 学习条件判断语法
- 掌握循环结构的使用

## 示例代码

```python
@name: "基本语法演示"
@description: "展示pytest-dsl的基本语法特性"

# ===== 变量定义和数据类型 =====

# 字符串变量
message = "Hello, pytest-dsl!"
user_name = "张三"

# 数字变量
age = 25
price = 19.99
count = 0

# 布尔变量
is_active = true
debug_mode = false

# 数组/列表
colors = ["红色", "蓝色", "绿色"]
numbers = [1, 2, 3, 4, 5]

# 对象/字典
user = {
    "name": "李四",
    "age": 30,
    "email": "lisi@example.com",
    "active": true
}

# ===== 变量使用演示 =====

[Print], 欢迎消息: ${message}
[Print], 用户姓名: ${user_name}
[Print], 年龄: ${age}
[Print], 价格: ${price}
[Print], 是否活跃: ${is_active}

# 访问对象属性
[Print], 用户对象 - 姓名: ${user.name}
[Print], 用户对象 - 年龄: ${user.age}
[Print], 用户对象 - 邮箱: ${user.email}

# 访问数组元素
[Print], 第一个颜色: ${colors[0]}
[Print], 第二个颜色: ${colors[1]}
[Print], 第一个数字: ${numbers[0]}

# ===== 条件判断 =====

# 简单if判断
if ${age} >= 18:
    [Print], ${user_name}已成年，年龄: ${age}
else:
    [Print], ${user_name}未成年，年龄: ${age}

# 多条件判断
if ${age} < 18:
    [Print], 年龄段: 未成年
elif ${age} < 60:
    [Print], 年龄段: 成年人
else:
    [Print], 年龄段: 老年人

# 布尔变量判断
if ${is_active}:
    [Print], 用户状态: 活跃
else:
    [Print], 用户状态: 非活跃

# 复合条件判断
if ${age} >= 18 and ${is_active}:
    [Print], 符合条件: 成年且活跃的用户
else:
    [Print], 不符合条件: 未成年或非活跃用户

# ===== 循环结构 =====

# 遍历数组
[Print], 遍历颜色列表:
for color in ${colors}:
    [Print], 颜色: ${color}

# 遍历数字
[Print], 遍历数字列表:
for num in ${numbers}:
    [Print], 数字: ${num}

# 带索引的循环
[Print], 带索引的循环:
for i, color in enumerate(${colors}):
    [Print], 索引 ${i}: ${color}

# 范围循环
[Print], 范围循环 (0-4):
for i in range(5):
    [Print], 当前索引: ${i}

# 条件循环
[Print], 条件循环演示:
while ${count} < 3:
    count = ${count} + 1
    [Print], 计数器: ${count}

# ===== 数据操作 =====

# 字符串操作
full_message = "${user_name}的年龄是${age}岁"
[Print], 拼接字符串: ${full_message}

# 数组操作
[Print], 颜色总数: ${len(colors)}
[Print], 数字总和: ${sum(numbers)}

# 数据类型转换
age_str = str(${age})
price_int = int(${price})
[Print], 年龄字符串: ${age_str}
[Print], 价格整数: ${price_int}

# ===== 嵌套结构演示 =====

# 嵌套if-for循环
[Print], 嵌套结构演示:
if ${len(colors)} > 0:
    [Print], 开始遍历颜色:
    for color in ${colors}:
        if ${color} == "红色":
            [Print], 找到红色!
        else:
            [Print], 其他颜色: ${color}

# 复杂数据结构
products = [
    {"name": "苹果", "price": 5.0, "category": "水果"},
    {"name": "牛奶", "price": 3.5, "category": "饮品"},
    {"name": "面包", "price": 2.0, "category": "主食"}
]

[Print], 产品信息:
for product in ${products}:
    [Print], 产品: ${product.name}, 价格: ${product.price}, 类别: ${product.category}
    
    if ${product.price} > 4.0:
        [Print], ${product.name} 价格较高
    else:
        [Print], ${product.name} 价格适中

# ===== 断言演示 =====

# 基本断言
[Should Be Equal], ${age}, 25
[Should Be Equal], ${user_name}, "张三"
[Should Be True], ${is_active}
[Should Be False], ${debug_mode}

# 数组断言
[Should Contain], ${colors}, "红色"
[Should Not Contain], ${colors}, "黄色"

# 数字比较断言
[Should Be True], ${age} >= 18
[Should Be True], ${price} > 0
[Should Be Equal], ${len(numbers)}, 5

[Print], 所有断言都通过了！

# ===== 完成提示 =====
[Print], 基本语法演示完成！
[Print], 您已经掌握了pytest-dsl的核心语法特性。
```

## 运行方式

### 方式一：直接运行

```bash
# 保存上述代码为 basic_syntax.dsl
pytest-dsl basic_syntax.dsl
```

### 方式二：pytest集成

```python
# test_basic_syntax.py
import pytest
from pytest_dsl import run_dsl_file

def test_basic_syntax():
    """测试基本语法功能"""
    result = run_dsl_file("basic_syntax.dsl")
    assert result.success
```

## 输出示例

```
欢迎消息: Hello, pytest-dsl!
用户姓名: 张三
年龄: 25
价格: 19.99
是否活跃: True
用户对象 - 姓名: 李四
用户对象 - 年龄: 30
用户对象 - 邮箱: lisi@example.com
第一个颜色: 红色
第二个颜色: 蓝色
第一个数字: 1
张三已成年，年龄: 25
年龄段: 成年人
用户状态: 活跃
符合条件: 成年且活跃的用户
遍历颜色列表:
颜色: 红色
颜色: 蓝色
颜色: 绿色
遍历数字列表:
数字: 1
数字: 2
数字: 3
数字: 4
数字: 5
...
所有断言都通过了！
基本语法演示完成！
您已经掌握了pytest-dsl的核心语法特性。
```

## 语法要点详解

### 1. 变量定义

pytest-dsl支持多种数据类型：

```python
# 基本类型
string_var = "字符串"
number_var = 42
float_var = 3.14
boolean_var = true

# 复合类型
array_var = [1, 2, 3]
object_var = {"key": "value"}
```

### 2. 变量引用

使用 `${variable}` 语法引用变量：

```python
name = "世界"
message = "你好，${name}!"  # 结果：你好，世界!
```

### 3. 条件判断

支持完整的条件判断语法：

```python
if condition:
    # 执行代码
elif another_condition:
    # 执行代码
else:
    # 执行代码
```

### 4. 循环结构

支持多种循环方式：

```python
# for循环
for item in ${array}:
    # 处理每个item

# 带索引的循环
for i, item in enumerate(${array}):
    # 处理item和索引

# 范围循环
for i in range(10):
    # 执行10次

# while循环
while ${condition}:
    # 执行代码
```

### 5. 数据访问

支持点号和方括号访问：

```python
# 对象属性访问
${user.name}
${user.profile.age}

# 数组索引访问
${colors[0]}
${matrix[1][2]}

# 混合访问
${users[0].name}
```

## 最佳实践

### 1. 命名规范

使用有意义的变量名：

```python
# 好的命名
user_name = "张三"
api_response = {...}
test_data = [...]

# 避免的命名
a = "张三"
x = {...}
data = [...]
```

### 2. 结构组织

保持代码结构清晰：

```python
# 1. 变量定义
user_id = 123
api_url = "https://api.example.com"

# 2. 数据准备
test_data = {...}

# 3. 主要逻辑
[HTTP请求], ...

# 4. 结果验证
[Should Be Equal], ...
```

### 3. 注释使用

添加适当的注释：

```python
# 用户信息配置
user = {
    "name": "测试用户",    # 用户名
    "role": "admin"       # 用户角色
}

# 执行API测试
[GET], ${api_url}/users/${user_id}
```

这个基本语法示例涵盖了pytest-dsl的核心语法特性，为后续的高级功能学习打下基础。 