@name: "布尔值使用演示"
@description: "演示True和False布尔值在pytest-dsl中的使用方法"
@tags: ["布尔值", "True", "False", "演示"]

# ============================================================================
# 布尔值使用演示
# 
# 本DSL文件演示了pytest-dsl中True和False布尔值的使用方法：
# 1. 直接赋值布尔值
# 2. 在条件语句中使用布尔值
# 3. 布尔值与比较运算符的结合使用
# 4. 布尔值在循环条件中的应用
# ============================================================================

# 测试1: 基本的布尔值赋值
[打印], 内容: "=== 测试1: 布尔值赋值 ==="

# 直接赋值True和False
is_enabled = True
is_disabled = False

[打印], 内容: "is_enabled的值: ${is_enabled}"
[打印], 内容: "is_disabled的值: ${is_disabled}"

# 测试2: 在条件语句中使用布尔值
[打印], 内容: "=== 测试2: 条件语句中的布尔值 ==="

if ${is_enabled} do
    [打印], 内容: "is_enabled为True，执行此分支"
else
    [打印], 内容: "is_enabled为False，不应该执行此分支"
end

if ${is_disabled} do
    [打印], 内容: "is_disabled为True，不应该执行此分支"
else
    [打印], 内容: "is_disabled为False，执行此分支"
end

# 测试3: 布尔值与比较运算符的结合
[打印], 内容: "=== 测试3: 布尔值比较 ==="

# 布尔值比较
bool_result1 = ${is_enabled} == True
bool_result2 = ${is_disabled} == False

[打印], 内容: "is_enabled == True 的结果: ${bool_result1}"
[打印], 内容: "is_disabled == False 的结果: ${bool_result2}"

# 使用布尔值比较结果作为条件
if ${bool_result1} do
    [打印], 内容: "布尔值比较结果为True"
end

# 测试4: 复杂的布尔逻辑
[打印], 内容: "=== 测试4: 复杂布尔逻辑 ==="

has_permission = True
is_admin = False
count = 5

# 组合条件判断
if ${has_permission} == True do
    [打印], 内容: "用户有权限"
    
    if ${count} > 3 do
        [打印], 内容: "数量大于3，并且用户有权限"
        
        if ${is_admin} == False do
            [打印], 内容: "用户不是管理员，但有权限且数量符合要求"
        end
    end
end

# 测试5: 在循环中使用布尔值
[打印], 内容: "=== 测试5: 循环中的布尔值 ==="

should_continue = True
loop_count = 0

for i in range(1, 6) do
    loop_count = ${loop_count} + 1
    [打印], 内容: "循环次数: ${loop_count}"
    
    if ${loop_count} == 3 do
        should_continue = False
        [打印], 内容: "循环3次后，设置should_continue为False"
    end
    
    # 使用布尔值作为continue条件
    if ${should_continue} == False do
        [打印], 内容: "should_continue为False，跳出循环"
        break
    end
end

[打印], 内容: "最终loop_count: ${loop_count}"
[打印], 内容: "最终should_continue: ${should_continue}"

[打印], 内容: "=== 布尔值演示完成 ===" 