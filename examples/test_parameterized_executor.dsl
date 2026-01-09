@name: "参数化执行机名称测试"
@description: "测试执行机名称可以参数化的功能"

# 定义执行机名称变量
pk_name = "windows"
another_pk = "linux"

# 测试1: 基本参数化执行机名称
temp_path = "${pk_name}" | [生成随机路径]
[打印], 内容: "参数化执行机生成的路径: ${temp_path}"

# 测试2: 使用不同的执行机名称
another_path = "${another_pk}" | [生成随机路径]
[打印], 内容: "另一个执行机生成的路径: ${another_path}"

# 测试3: 在循环中使用参数化执行机
executors = ["windows", "linux", "mac"]
for executor in executors do
    loop_path = "${executor}" | [生成随机路径]
    [打印], 内容: "循环中 ${executor} 生成的路径: ${loop_path}"
end

# 测试4: 验证生成的路径不为空
[断言], 条件: "len('${temp_path}') > 0", 消息: "生成的路径应该不为空"
[断言], 条件: "len('${another_path}') > 0", 消息: "另一个生成的路径应该不为空"