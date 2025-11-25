@name: "in运算符测试"
@description: "测试if语句中的in和not in运算符"
@tags: ["in运算符", "测试"]

# 测试1: 列表中的in运算符
[打印], 内容: "=== 测试1: 列表中的in运算符 ==="
items = ["apple", "banana", "orange"]
item = "apple"

if ${item} in ${items} do
    [打印], 内容: "✓ ${item} 在列表中"
else
    [打印], 内容: "✗ ${item} 不在列表中"
end

# 测试2: 列表中的not in运算符
[打印], 内容: "=== 测试2: 列表中的not in运算符 ==="
item2 = "grape"

if ${item2} not in ${items} do
    [打印], 内容: "✓ ${item2} 不在列表中"
else
    [打印], 内容: "✗ ${item2} 在列表中"
end

# 测试3: 字符串中的in运算符
[打印], 内容: "=== 测试3: 字符串中的in运算符 ==="
text = "Hello, World!"
substring = "World"

if ${substring} in ${text} do
    [打印], 内容: "✓ '${substring}' 在字符串中"
else
    [打印], 内容: "✗ '${substring}' 不在字符串中"
end

# 测试4: 字典键中的in运算符
[打印], 内容: "=== 测试4: 字典键中的in运算符 ==="
user = {"name": "张三", "age": 25, "city": "北京"}
key = "name"

if ${key} in ${user} do
    [打印], 内容: "✓ '${key}' 是字典的键"
else
    [打印], 内容: "✗ '${key}' 不是字典的键"
end

# 测试5: in与其他运算符组合
[打印], 内容: "=== 测试5: in与其他运算符组合 ==="
numbers = [1, 2, 3, 4, 5]
num = 3

if ${num} in ${numbers} and ${num} > 2 do
    [打印], 内容: "✓ ${num} 在列表中且大于2"
else
    [打印], 内容: "✗ 条件不满足"
end

# 测试6: not in与其他运算符组合
[打印], 内容: "=== 测试6: not in与其他运算符组合 ==="
status = "active"
valid_statuses = ["active", "pending"]

if ${status} not in ${valid_statuses} or ${status} == "inactive" do
    [打印], 内容: "✓ 状态不在有效列表中或是inactive"
else
    [打印], 内容: "✗ 状态在有效列表中且不是inactive"
end

[打印], 内容: "=== in运算符测试完成 ==="

