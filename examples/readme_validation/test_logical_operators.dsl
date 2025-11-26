@name: "逻辑运算符测试"
@description: "测试if语句中的and、or、not逻辑运算符"
@tags: ["逻辑运算符", "测试"]

# 测试1: and运算符
[打印], 内容: "=== 测试1: and运算符 ==="
user_role = "admin"
user_active = True

if user_role == "admin" and ${user_active} do
    [打印], 内容: "✓ 管理员用户且状态活跃"
else
    [打印], 内容: "✗ 条件不满足"
end

# 测试2: 多个and组合
[打印], 内容: "=== 测试2: 多个and组合 ==="
age = 25
country = "China"

if ${age} >= 18 and country == "China" do
    [打印], 内容: "✓ 符合条件的中国成年用户"
else
    [打印], 内容: "✗ 条件不满足"
end

# 测试3: or运算符
[打印], 内容: "=== 测试3: or运算符 ==="
user_type = "premium"

if user_type == "premium" or user_type == "vip" do
    [打印], 内容: "✓ 高级用户，享受特殊权限"
else
    [打印], 内容: "✗ 不是高级用户"
end

# 测试4: not运算符
[打印], 内容: "=== 测试4: not运算符 ==="
is_banned = False

if not ${is_banned} do
    [打印], 内容: "✓ 用户未被封禁，可以正常使用"
else
    [打印], 内容: "✗ 用户被封禁"
end

# 测试5: 复杂逻辑组合
[打印], 内容: "=== 测试5: 复杂逻辑组合 ==="
score = 85
is_vip = True

if ${score} >= 80 and ${is_vip} do
    [打印], 内容: "✓ 高分VIP用户"
elif ${score} >= 80 or ${is_vip} do
    [打印], 内容: "✓ 高分或VIP用户"
else
    [打印], 内容: "✗ 普通用户"
end

# 测试6: not与其他运算符组合
[打印], 内容: "=== 测试6: not与其他运算符组合 ==="
status = "inactive"

if not status == "active" do
    [打印], 内容: "✓ 状态不是active"
else
    [打印], 内容: "✗ 状态是active"
end

# 测试7: 括号优先级测试
[打印], 内容: "=== 测试7: 括号优先级测试 ==="
x = 5
y = 10
z = 15

if (${x} > 3 and ${y} < 20) or ${z} > 20 do
    [打印], 内容: "✓ 括号优先级正确"
else
    [打印], 内容: "✗ 括号优先级错误"
end

[打印], 内容: "=== 逻辑运算符测试完成 ==="

