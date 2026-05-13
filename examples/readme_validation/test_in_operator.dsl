@name: "in运算符测试"
@description: "测试if语句中的in和not in运算符"
@tags: ["in运算符", "测试"]

# 测试1: 列表中的in运算符
[打印], 内容: "=== 测试1: 列表中的in运算符 ==="
items = ["apple", "banana", "orange"]
item = "apple"
case1_result = "未执行"

if ${item} in ${items} do
    case1_result = "通过"
    [打印], 内容: "✓ ${item} 在列表中"
else
    case1_result = "失败"
    [打印], 内容: "✗ ${item} 不在列表中"
end

# 测试2: 列表中的not in运算符
[打印], 内容: "=== 测试2: 列表中的not in运算符 ==="
item2 = "grape"
case2_result = "未执行"

if ${item2} not in ${items} do
    case2_result = "通过"
    [打印], 内容: "✓ ${item2} 不在列表中"
else
    case2_result = "失败"
    [打印], 内容: "✗ ${item2} 在列表中"
end

# 测试3: 字符串中的in运算符
[打印], 内容: "=== 测试3: 字符串中的in运算符 ==="
text = "Hello, World!"
substring = "World"
case3_result = "未执行"

if ${substring} in ${text} do
    case3_result = "通过"
    [打印], 内容: "✓ '${substring}' 在字符串中"
else
    case3_result = "失败"
    [打印], 内容: "✗ '${substring}' 不在字符串中"
end

# 测试4: 字典键中的in运算符
[打印], 内容: "=== 测试4: 字典键中的in运算符 ==="
user = {"name": "张三", "age": 25, "city": "北京"}
key = "name"
case4_result = "未执行"

if ${key} in ${user} do
    case4_result = "通过"
    [打印], 内容: "✓ '${key}' 是字典的键"
else
    case4_result = "失败"
    [打印], 内容: "✗ '${key}' 不是字典的键"
end

# 测试5: in与其他运算符组合
[打印], 内容: "=== 测试5: in与其他运算符组合 ==="
numbers = [1, 2, 3, 4, 5]
num = 3
case5_result = "未执行"

if ${num} in ${numbers} and ${num} > 2 do
    case5_result = "通过"
    [打印], 内容: "✓ ${num} 在列表中且大于2"
else
    case5_result = "失败"
    [打印], 内容: "✗ 条件不满足"
end

# 测试6: not in与其他运算符组合
[打印], 内容: "=== 测试6: not in与其他运算符组合 ==="
status = "active"
valid_statuses = ["active", "pending"]
case6_result = "未执行"

if ${status} not in ${valid_statuses} or ${status} == "inactive" do
    case6_result = "失败"
    [打印], 内容: "✓ 状态不在有效列表中或是inactive"
else
    case6_result = "通过"
    [打印], 内容: "✗ 状态在有效列表中且不是inactive"
end

[断言], 条件: "${case1_result} == '通过'", 消息: "列表in运算符分支错误"
[断言], 条件: "${case2_result} == '通过'", 消息: "列表not in运算符分支错误"
[断言], 条件: "${case3_result} == '通过'", 消息: "字符串in运算符分支错误"
[断言], 条件: "${case4_result} == '通过'", 消息: "字典键in运算符分支错误"
[断言], 条件: "${case5_result} == '通过'", 消息: "in与and组合分支错误"
[断言], 条件: "${case6_result} == '通过'", 消息: "not in与or组合分支错误"

[打印], 内容: "=== in运算符测试完成 ==="
