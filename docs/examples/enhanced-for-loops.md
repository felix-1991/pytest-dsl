# 增强的for循环语法

pytest-dsl现在支持三种不同的for循环语法，让数据遍历更加灵活和直观。

## 支持的循环类型

### 1. 传统range循环（向后兼容）

```dsl
# 语法：for 变量 in range(开始, 结束) do ... end
for i in range(0, 5) do
    [打印], 内容: "索引: ${i}"
end
```

**说明：**
- 保持完全向后兼容
- 生成从开始值到结束值-1的整数序列
- 适用于需要索引控制的场景

### 2. 数组/列表遍历循环

```dsl
# 语法：for 元素变量 in 数组变量 do ... end
fruits = ["苹果", "香蕉", "橙子"]
for fruit in fruits do
    [打印], 内容: "水果: ${fruit}"
end
```

**特性：**
- 直接遍历数组中的每个元素
- 支持字符串、数字、布尔值、对象等混合类型数组
- 自动处理空数组（不执行循环体）

**支持的数据类型：**
```dsl
# 字符串数组
names = ["张三", "李四", "王五"]
for name in names do
    [打印], 内容: "姓名: ${name}"
end

# 数字数组
numbers = [10, 20, 30, 40]
total = 0
for num in numbers do
    total = ${total} + ${num}
end

# 混合类型数组
mixed = ["文本", 123, True, {"key": "value"}]
for item in mixed do
    [打印], 内容: "项目: ${item}"
end
```

### 3. 字典键值对遍历循环

```dsl
# 语法：for 键变量, 值变量 in 字典变量 do ... end
user = {
    "name": "张三",
    "age": 30,
    "city": "北京"
}

for key, value in user do
    [打印], 内容: "${key}: ${value}"
end
```

**特性：**
- 同时获取字典的键和值
- 键和值变量名必须不同
- 自动处理空字典（不执行循环体）

## 实际应用示例

### 数据处理示例

```dsl
@name: "数据处理示例"
@description: "使用新for循环语法处理各种数据结构"

# 处理用户列表
users = [
    {"name": "张三", "age": 25, "role": "开发者"},
    {"name": "李四", "age": 30, "role": "测试员"},
    {"name": "王五", "age": 28, "role": "产品经理"}
]

[打印], 内容: "=== 用户信息处理 ==="
for user in users do
    [打印], 内容: "姓名: ${user.name}, 年龄: ${user.age}, 角色: ${user.role}"
    
    # 根据角色进行不同处理
    if ${user.role} == "开发者" do
        [打印], 内容: "  → 分配开发任务"
    elif ${user.role} == "测试员" do
        [打印], 内容: "  → 分配测试任务"
    else
        [打印], 内容: "  → 分配管理任务"
    end
end

# 处理配置信息
config = {
    "timeout": 30,
    "retries": 3,
    "debug": True,
    "log_level": "INFO"
}

[打印], 内容: "=== 配置信息验证 ==="
for setting, value in config do
    [打印], 内容: "配置项: ${setting} = ${value}"
    
    # 验证特定配置
    if ${setting} == "timeout" do
        if ${value} < 10 do
            [打印], 内容: "  ⚠️ 超时时间过短"
        end
    elif ${setting} == "debug" do
        if ${value} == True do
            [打印], 内容: "  🐛 调试模式已启用"
        end
    end
end
```

### 嵌套循环示例

```dsl
@name: "嵌套循环处理"
@description: "多层数据结构的处理"

# 部门和员工的嵌套结构
departments = {
    "技术部": {
        "manager": "李经理",
        "employees": ["小王", "小张", "小李"],
        "budget": 100000
    },
    "销售部": {
        "manager": "陈经理", 
        "employees": ["小刘", "小赵"],
        "budget": 80000
    }
}

total_employees = 0
total_budget = 0

for dept_name, dept_info in departments do
    [打印], 内容: "部门: ${dept_name}"
    [打印], 内容: "  经理: ${dept_info.manager}"
    [打印], 内容: "  预算: ${dept_info.budget}"
    
    total_budget = ${total_budget} + ${dept_info.budget}
    
    [打印], 内容: "  员工列表:"
    for employee in dept_info.employees do
        [打印], 内容: "    - ${employee}"
        total_employees = ${total_employees} + 1
    end
end

[打印], 内容: "=== 统计结果 ==="
[打印], 内容: "总员工数: ${total_employees}"
[打印], 内容: "总预算: ${total_budget}"
```

### 控制流语句支持

所有类型的for循环都支持`break`和`continue`语句：

```dsl
@name: "循环控制示例"

# 在数组遍历中使用break和continue
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
even_sum = 0

for num in numbers do
    # 跳过奇数
    mod_result = ${num} % 2
    if ${mod_result} != 0 do
        continue
    end
    
    # 累加偶数
    even_sum = ${even_sum} + ${num}
    [打印], 内容: "累加偶数: ${num}, 当前和: ${even_sum}"
    
    # 达到某个条件时退出
    if ${even_sum} >= 12 do
        [打印], 内容: "偶数和已达到12，退出循环"
        break
    end
end

# 在字典遍历中使用控制语句
sensitive_config = {
    "public_key": "公开密钥",
    "timeout": 30,
    "secret_key": "敏感信息",
    "debug": True
}

for key, value in sensitive_config do
    # 跳过敏感信息
    if ${key} == "secret_key" do
        [打印], 内容: "跳过敏感配置: ${key}"
        continue
    end
    
    [打印], 内容: "配置: ${key} = ${value}"
end
```

## 错误处理和最佳实践

### 类型检查

```dsl
# 确保变量是可遍历的
test_data = [1, 2, 3]

# 好的做法：在遍历前检查类型
if ${test_data} != null do
    for item in test_data do
        [打印], 内容: "处理: ${item}"
    end
else
    [打印], 内容: "数据为空，跳过处理"
end
```

### 变量命名建议

```dsl
# 使用有意义的变量名
users = [{"name": "张三"}, {"name": "李四"}]

# 好的命名
for user in users do
    [打印], 内容: "用户: ${user.name}"
end

# 字典遍历时使用描述性名称
config = {"timeout": 30, "debug": True}

# 好的命名
for setting_name, setting_value in config do
    [打印], 内容: "${setting_name}: ${setting_value}"
end
```

### 性能考虑

1. **空集合检查**：框架自动处理空数组和空字典，不会执行循环体
2. **大数据集**：对于大型数据集，考虑在循环中添加适当的日志和进度提示
3. **深层嵌套**：避免过深的嵌套循环，必要时可以拆分为多个函数

## 语法对比

| 循环类型 | 旧语法 | 新语法 | 适用场景 |
|---------|--------|--------|----------|
| 索引循环 | `for i in range(0, 5)` | 同左（保持兼容） | 需要索引控制 |
| 数组遍历 | 需要range+索引访问 | `for item in array` | 直接处理元素 |
| 字典遍历 | 不支持 | `for key, value in dict` | 键值对处理 |

## 兼容性说明

- ✅ 完全向后兼容现有的range循环语法
- ✅ 支持所有现有的循环控制语句（break, continue）
- ✅ 支持嵌套循环和复杂数据结构
- ✅ 与变量系统和远程关键字无缝集成 [[memory:3307036]]

## 总结

新的for循环语法让pytest-dsl在处理复杂数据结构时更加强大和直观：

1. **数组遍历**：`for item in array` - 直接访问每个元素
2. **字典遍历**：`for key, value in dict` - 同时获取键和值  
3. **向后兼容**：保持对现有range循环的完全支持

这些增强使得数据驱动测试和复杂场景处理变得更加简单和自然。 [[memory:3307030]] 