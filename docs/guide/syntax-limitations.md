# DSL 语法限制说明

本文档详细说明了当前 pytest-dsl 语法的限制和相应的替代方案。

## 循环语法限制

### 不支持的语法

#### 1. 直接遍历数组
```python
# ❌ 不支持
for item in ${array} do
    [打印], 内容: ${item}
end

# ❌ 不支持
for user in ${users} do
    [打印], 内容: ${user.name}
end
```

#### 2. 带索引的数组遍历
```python
# ❌ 不支持
for i, item in enumerate(${array}) do
    [打印], 内容: "索引${i}: ${item}"
end
```

#### 3. 字典遍历
```python
# ❌ 不支持
for key in ${dict} do
    [打印], 内容: "${key}: ${dict[key]}"
end

# ❌ 不支持
for key, value in ${dict.items()} do
    [打印], 内容: "${key}: ${value}"
end
```

#### 4. while 循环
```python
# ❌ 不支持
while ${condition} do
    # 循环体
end
```

### 支持的替代方案

#### 1. 使用索引遍历数组
```python
# ✅ 支持
array = ["item1", "item2", "item3"]
array_length = 3  # 需要预定义长度

for i in range(0, ${array_length}) do
    [打印], 内容: ${array[i]}
end
```

#### 2. 遍历对象数组
```python
# ✅ 支持
users = [
    {"name": "张三", "age": 25},
    {"name": "李四", "age": 30}
]
users_length = 2

for i in range(0, ${users_length}) do
    [打印], 内容: "用户: ${users[i].name}, 年龄: ${users[i].age}"
end
```

#### 3. 遍历字典键
```python
# ✅ 支持
user_info = {"name": "张三", "age": 30, "city": "北京"}
keys = ["name", "age", "city"]  # 预定义键列表
keys_length = 3

for i in range(0, ${keys_length}) do
    key = ${keys[i]}
    value = ${user_info[key]}
    [打印], 内容: "${key}: ${value}"
end
```

#### 4. 使用 for + break 模拟 while
```python
# ✅ 支持 - 模拟 while 循环
max_attempts = 10
attempt = 0

for i in range(0, ${max_attempts}) do
    attempt = attempt + 1
    
    # 执行操作
    [HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: /api/status
        captures:
            status: ["jsonpath", "$.status"]
    '''
    
    # 检查退出条件
    if ${status} == "ready" do
        [打印], 内容: "服务就绪，退出循环"
        break
    end
    
    [等待], 秒数: 1
end
```

## 占位符语法限制

### 不支持的语法

#### 1. 函数调用
```python
# ❌ 不支持
array = [1, 2, 3, 4, 5]
length = ${len(array)}

# ❌ 不支持
text = "hello"
upper_text = ${text.upper()}

# ❌ 不支持
numbers = [1, 2, 3, 4, 5]
total = ${sum(numbers)}
```

#### 2. 算术运算
```python
# ❌ 不支持
count = 5
next_count = ${count + 1}

# ❌ 不支持
price = 100
tax = ${price * 0.1}
```

#### 3. 比较运算
```python
# ❌ 不支持
age = 18
is_adult = ${age >= 18}
```

#### 4. 类型转换
```python
# ❌ 不支持
number = 123
text = ${str(number)}

# ❌ 不支持
text = "123"
number = ${int(text)}
```

### 支持的替代方案

#### 1. 预定义变量
```python
# ✅ 支持
array = [1, 2, 3, 4, 5]
array_length = 5  # 手动指定长度

# ✅ 支持
text = "hello"
upper_text = "HELLO"  # 手动指定转换结果
```

#### 2. 使用表达式语法
```python
# ✅ 支持 - 在赋值中使用算术运算
count = 5
next_count = count + 1

# ✅ 支持 - 在条件中使用比较运算
age = 18
if age >= 18 do
    [打印], 内容: "已成年"
end
```

#### 3. 使用关键字处理复杂逻辑
```python
# ✅ 支持 - 使用字符串操作关键字
text = "hello"
upper_text = [字符串操作], 操作: "upper", 字符串: ${text}

# ✅ 支持 - 使用断言关键字进行条件判断
age = 18
[断言], 条件: "${age} >= 18", 消息: "年龄验证"
```

## 条件语句语法

### 支持的语法
```python
# ✅ 支持 - 标准 if-elif-else 结构
if ${condition1} do
    # 代码块1
elif ${condition2} do
    # 代码块2
else
    # 代码块3
end
```

### 不支持的语法
```python
# ❌ 不支持 - Python 风格的冒号语法
if condition:
    # 代码块

# ❌ 不支持 - 三元运算符
result = value1 if condition else value2
```

## 变量赋值限制

### 支持的语法
```python
# ✅ 支持 - 直接赋值
name = "张三"
age = 25
active = True

# ✅ 支持 - 从关键字返回值赋值
result = [HTTP请求], 客户端: "default", 配置: "..."

# ✅ 支持 - 算术运算赋值
total = a + b
difference = a - b
```

### 不支持的语法
```python
# ❌ 不支持 - 多重赋值
a, b = 1, 2

# ❌ 不支持 - 增量赋值
count += 1
total *= 2

# ❌ 不支持 - 解构赋值
name, age = user_data
```

## 数据结构限制

### 支持的语法
```python
# ✅ 支持 - 列表字面量
numbers = [1, 2, 3, 4, 5]
names = ["张三", "李四", "王五"]

# ✅ 支持 - 字典字面量
user = {
    "name": "张三",
    "age": 30,
    "active": True
}

# ✅ 支持 - 嵌套结构
data = {
    "users": [
        {"name": "张三", "age": 25},
        {"name": "李四", "age": 30}
    ],
    "config": {
        "timeout": 30,
        "retries": 3
    }
}
```

### 访问语法
```python
# ✅ 支持 - 数组索引访问
first_item = ${numbers[0]}
last_item = ${numbers[-1]}

# ✅ 支持 - 字典键访问
user_name = ${user["name"]}
user_age = ${user.age}

# ✅ 支持 - 嵌套访问
first_user_name = ${data.users[0].name}
timeout_config = ${data["config"]["timeout"]}
```

## 最佳实践建议

### 1. 预定义数组长度
```python
# 推荐做法
test_data = ["case1", "case2", "case3"]
test_data_length = 3  # 明确指定长度

for i in range(0, ${test_data_length}) do
    [执行测试], 用例: ${test_data[i]}
end
```

### 2. 使用描述性变量名
```python
# 推荐做法
users_count = 5
max_retry_attempts = 3
api_timeout_seconds = 30

# 避免使用魔法数字
for i in range(0, ${users_count}) do
    # 处理用户
end
```

### 3. 合理使用关键字
```python
# 推荐做法 - 使用内置关键字处理复杂逻辑
text_length = [字符串操作], 操作: "length", 字符串: ${input_text}
random_value = [生成随机数], 最小值: 1, 最大值: 100

# 而不是尝试使用不支持的函数调用
# length = ${len(input_text)}  # 不支持
```

### 4. 错误处理
```python
# 推荐做法 - 使用条件判断进行错误处理
if ${response_status} != 200 do
    [打印], 内容: "API请求失败，状态码: ${response_status}"
    return "失败"
end

[打印], 内容: "API请求成功"
```

### 5. 代码组织
```python
# 推荐做法 - 将复杂逻辑封装为自定义关键字
function 批量处理用户 (用户列表, 批次大小=10) do
    用户数量 = ${用户列表.length}  # 假设有length属性
    
    for i in range(0, ${用户数量}) do
        [处理单个用户], 用户: ${用户列表[i]}
        
        # 每处理一定数量后暂停
        if (i + 1) % ${批次大小} == 0 do
            [等待], 秒数: 1
        end
    end
end
```

## 语法检查工具

建议在编写 DSL 代码时：

1. **使用 VSCode 扩展** - 提供语法高亮和基本错误检查
2. **运行语法验证** - 使用 `pytest-dsl-list` 命令检查关键字是否正确加载
3. **查看解析错误** - 注意词法分析器和语法分析器的错误信息
4. **参考示例代码** - 查看 `docs/examples` 目录中的正确示例

## 未来改进计划

以下功能可能在未来版本中支持：

1. **增强的循环语法** - 支持直接遍历数组和字典
2. **函数调用支持** - 在占位符中支持内置函数调用
3. **算术表达式** - 在占位符中支持复杂的算术运算
4. **类型系统** - 提供更好的类型检查和转换
5. **模式匹配** - 支持更复杂的条件匹配语法

在此之前，请使用本文档中描述的替代方案来实现所需功能。 