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

[打印], 内容: 欢迎消息: ${message}
[打印], 内容: 用户姓名: ${user_name}
[打印], 内容: 年龄: ${age}
[打印], 内容: 价格: ${price}
[打印], 内容: 是否活跃: ${is_active}

# 访问对象属性
[打印], 内容: 用户对象 - 姓名: ${user.name}
[打印], 内容: 用户对象 - 年龄: ${user.age}
[打印], 内容: 用户对象 - 邮箱: ${user.email}

# 访问数组元素
[打印], 内容: 第一个颜色: ${colors[0]}
[打印], 内容: 第二个颜色: ${colors[1]}
[打印], 内容: 第一个数字: ${numbers[0]}

# ===== 条件判断 =====

# 简单if判断
if ${age} >= 18 do
    [打印], 内容: ${user_name}已成年，年龄: ${age}
else
    [打印], 内容: ${user_name}未成年，年龄: ${age}
end

# 多条件判断
if ${age} < 18 do
    [打印], 内容: 年龄段: 未成年
elif ${age} < 60 do
    [打印], 内容: 年龄段: 成年人
else
    [打印], 内容: 年龄段: 老年人
end

# 布尔变量判断
if ${is_active} do
    [打印], 内容: 用户状态: 活跃
else
    [打印], 内容: 用户状态: 非活跃
end

# 复合条件判断
if ${age} >= 18 and ${is_active} do
    [打印], 内容: 符合条件: 成年且活跃的用户
else
    [打印], 内容: 不符合条件: 未成年或非活跃用户
end

# ===== 循环结构 =====

# 范围循环 - 当前支持的语法
[打印], 内容: 范围循环 (0-4):
for i in range(0, 5) do
    [打印], 内容: 当前索引: ${i}
end

# 注意：由于当前不支持 ${len(array)} 语法，
# 需要预先定义数组长度或使用固定范围

# 预定义数组长度
colors_length = 3
numbers_length = 5

# 模拟遍历数组 - 使用预定义长度
[打印], 内容: 遍历颜色列表:
for i in range(0, ${colors_length}) do
    [打印], 内容: 颜色: ${colors[i]}
end

# 模拟遍历数字数组
[打印], 内容: 遍历数字列表:
for i in range(0, ${numbers_length}) do
    [打印], 内容: 数字: ${numbers[i]}
end

# 注意：当前版本暂不支持以下语法：
# - for item in array (直接遍历数组)
# - for i, item in enumerate(array) (带索引遍历)
# - while 循环
# 这些功能将在后续版本中添加

# ===== 数据操作 =====

# 字符串操作
full_message = "${user_name}的年龄是${age}岁"
[打印], 内容: 拼接字符串: ${full_message}

# 数组操作 - 注意：当前不支持内置函数调用
# 需要手动计算或预定义值
[打印], 内容: 颜色总数: ${colors_length}
# [打印], 内容: 数字总和: ${sum(numbers)}  # 不支持

# 数据类型转换 - 注意：当前不支持函数调用语法
# age_str = str(${age})  # 不支持
# price_int = int(${price})  # 不支持
# 需要使用字符串操作关键字或其他方式进行转换
[字符串操作], 操作: "concat", 字符串: "", 参数1: ${age}, 参数2: ""

# ===== 嵌套结构演示 =====

# 嵌套if-for循环
[打印], 内容: 嵌套结构演示:
if ${colors_length} > 0 do
    [打印], 内容: 开始遍历颜色:
    for i in range(0, ${colors_length}) do
        if ${colors[i]} == "红色" do
            [打印], 内容: 找到红色!
        else
            [打印], 内容: 其他颜色: ${colors[i]}
        end
    end
end

# 复杂数据结构
products = [
    {"name": "苹果", "price": 5.0, "category": "水果"},
    {"name": "牛奶", "price": 3.5, "category": "饮品"},
    {"name": "面包", "price": 2.0, "category": "主食"}
]

# 预定义产品数组长度
products_length = 3

[打印], 内容: 产品信息:
for i in range(0, ${products_length}) do
    [打印], 内容: 产品: ${products[i].name}, 价格: ${products[i].price}, 类别: ${products[i].category}
    
    if ${products[i].price} > 4.0 do
        [打印], 内容: ${products[i].name} 价格较高
    else
        [打印], 内容: ${products[i].name} 价格适中
    end
end

# ===== 断言演示 =====

# 基本断言
[数据比较], 实际值: ${age}, 预期值: 25
[数据比较], 实际值: ${user_name}, 预期值: "张三"
[断言], 条件: "${is_active} == True"
[断言], 条件: "${debug_mode} == False"

# 数组断言 - 使用断言关键字检查数组内容
[断言], 条件: "'红色' in ${colors}"
[断言], 条件: "'黄色' not in ${colors}"

# 数字比较断言
[断言], 条件: "${age} >= 18"
[断言], 条件: "${price} > 0"
[数据比较], 实际值: ${numbers_length}, 预期值: 5

[打印], 内容: 所有断言都通过了！

# ===== 完成提示 =====
[打印], 内容: 基本语法演示完成！
[打印], 内容: 您已经掌握了pytest-dsl的核心语法特性。
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

**当前支持的占位符语法：**
- `${variable}` - 简单变量引用
- `${obj.property}` - 对象属性访问
- `${array[0]}` - 数组索引访问
- `${obj[0].prop}` - 混合访问

**当前不支持的语法：**
- `${len(array)}` - 函数调用
- `${count + 1}` - 算术运算
- `${age >= 18}` - 比较运算（需要在条件表达式中使用）

### 3. 条件判断

支持完整的条件判断语法：

```python
if condition do
    # 执行代码
elif another_condition do
    # 执行代码
else
    # 执行代码
end
```

### 4. 循环结构

当前支持的循环方式：

```python
# 范围循环（当前唯一支持的循环语法）
for i in range(start, end) do
    # 执行代码
end

# 模拟数组遍历（使用预定义长度）
array_length = 5  # 需要预先定义数组长度
for i in range(0, ${array_length}) do
    # 使用 ${array[i]} 访问元素
end
```

**注意：** 以下语法暂不支持，将在后续版本中添加：
- `for item in array` - 直接遍历数组
- `for i, item in enumerate(array)` - 带索引遍历  
- `while condition` - while循环
- `${len(array)}` - 占位符内的函数调用
- `${expr + 1}` - 占位符内的算术运算

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