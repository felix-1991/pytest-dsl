@name: "Break和Continue功能演示"
@description: "演示for循环中的break和continue语句功能，包括基本用法、复合条件和嵌套场景"
@tags: ["循环控制", "break", "continue", "演示"]

# ============================================================================
# Break和Continue功能演示
# 
# 本DSL文件演示了pytest-dsl中for循环的break和continue控制语句功能：
# 1. break: 立即退出当前循环
# 2. continue: 跳过当前循环的剩余部分，继续下一次迭代
# 
# 支持的场景：
# - 基本的break和continue
# - 复合条件判断
# - 嵌套条件
# - 与算术运算符配合使用（如模运算%）
# ============================================================================

# 测试1: 基本的break功能
[打印], 内容: "=== 测试1: Break功能 ==="
test_result = ""

for i in range(1, 6) do
    if ${i} == 3 do
        [打印], 内容: "遇到break条件，退出循环"
        break
    end
    test_result = "${test_result}${i}"
    [打印], 内容: "累加结果: ${test_result}"
end

[打印], 内容: "Break测试最终结果: ${test_result} (预期: 12)"

# 测试2: 基本的continue功能
[打印], 内容: "=== 测试2: Continue功能 ==="
test_result2 = ""

for j in range(1, 6) do
    if ${j} == 3 do
        [打印], 内容: "遇到continue条件，跳过本次循环"
        continue
    end
    test_result2 = "${test_result2}${j}"
    [打印], 内容: "累加结果: ${test_result2}"
end

[打印], 内容: "Continue测试最终结果: ${test_result2} (预期: 1245)"

# 测试3: 复合条件下的break和continue（演示模运算%的使用）
[打印], 内容: "=== 测试3: 复合条件测试 ==="
odd_sum = 0

for k in range(1, 11) do
    [打印], 内容: "当前k: ${k}"
    
    # 如果是8，使用break退出
    if ${k} == 8 do
        [打印], 内容: "k=8，退出循环"
        break
    end
    
    # 计算模运算
    mod_result = ${k} % 2
    [打印], 内容: "k % 2 = ${mod_result}"
    
    # 如果是偶数，跳过
    if ${mod_result} == 0 do
        [打印], 内容: "k是偶数，跳过"
        continue
    end
    
    # 累加奇数
    odd_sum = ${odd_sum} + ${k}
    [打印], 内容: "累加奇数后: ${odd_sum}"
end

[打印], 内容: "奇数累加结果: ${odd_sum} (预期: 16，即1+3+5+7)"

# 测试4: 嵌套条件中的break和continue
[打印], 内容: "=== 测试4: 嵌套条件测试 ==="
result_list = []

for m in range(1, 6) do
    [打印], 内容: "当前m: ${m}"
    
    if ${m} > 3 do
        [打印], 内容: "m > 3"
        if ${m} == 5 do
            [打印], 内容: "m=5，退出循环"
            break
        end
        [打印], 内容: "m > 3 但不等于5，继续下次循环"
        continue
    else
        [打印], 内容: "m <= 3，添加到列表"
        result_list = ${result_list} + [${m}]
        [打印], 内容: "当前列表: ${result_list}"
    end
end

[打印], 内容: "嵌套条件测试最终列表: ${result_list} (预期: [1, 2, 3])"

[打印], 内容: "=== 所有测试完成 ===" 