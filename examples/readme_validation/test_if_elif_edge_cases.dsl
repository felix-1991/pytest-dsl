@name: "if-elif-else边界情况测试"
@description: "测试if-elif-else的各种边界情况"

# 测试1: 只有if，没有elif和else
[打印], 内容: "=== 测试1: 只有if ==="
value1 = 5
if value1 > 3 do
    [打印], 内容: "value1大于3"
end

# 测试2: if + 单个elif，没有else
[打印], 内容: "=== 测试2: if + 单个elif ==="
value2 = 2
if value2 > 5 do
    [打印], 内容: "value2大于5"
elif value2 > 1 do
    [打印], 内容: "value2大于1但不大于5"
end

# 测试3: 所有条件都为假，没有else
[打印], 内容: "=== 测试3: 所有条件为假，无else ==="
value3 = 0
if value3 > 5 do
    [打印], 内容: "不会执行"
elif value3 > 3 do
    [打印], 内容: "也不会执行"
elif value3 > 1 do
    [打印], 内容: "还是不会执行"
end
[打印], 内容: "继续执行后续代码"

# 测试4: 使用变量和字典的复杂条件
[打印], 内容: "=== 测试4: 复杂条件 ==="
user = {"role": "admin", "level": 5}
user_role = ${user["role"]}
user_level = ${user["level"]}

if user_role == "admin" do
    if user_level >= 5 do
        [打印], 内容: "高级管理员"
    elif user_level >= 3 do
        [打印], 内容: "中级管理员"
    else
        [打印], 内容: "初级管理员"
    end
elif user_role == "user" do
    [打印], 内容: "普通用户"
else
    [打印], 内容: "未知角色"
end

# 测试5: 布尔值条件
[打印], 内容: "=== 测试5: 布尔值条件 ==="
is_enabled = True
is_premium = False

if is_enabled == True do
    if is_premium == True do
        [打印], 内容: "高级用户已启用"
    else
        [打印], 内容: "普通用户已启用"
    end
elif is_enabled == False do
    [打印], 内容: "用户已禁用"
end

[打印], 内容: "=== 边界情况测试完成 ==="
