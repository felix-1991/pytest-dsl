@name: "数据驱动测试示例"
@data: "data_driven.csv" using csv
@description: "使用CSV数据测试登录功能（注意：需要用pytest运行）"

# 这个示例展示了数据驱动测试的语法
# 实际运行需要使用pytest命令，而不是pytest-dsl命令

# CSV中的每一行都会执行一次这个测试
[打印], 内容: "测试用例: ${test_case}"
[打印], 内容: "用户名: ${username}, 密码: ${password}, 期望状态: ${expected_status}"

# 模拟HTTP请求（实际应该是真实的API调用）
[打印], 内容: "模拟登录请求..."

# 简单的条件判断来模拟不同的测试结果
if "${username}" == "admin" do
    [打印], 内容: "管理员登录测试"
elif "${username}" == "user" do
    [打印], 内容: "普通用户登录测试"
else
    [打印], 内容: "无效用户登录测试"
end

[打印], 内容: "测试用例: ${test_case} - 完成"
