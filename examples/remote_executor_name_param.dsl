@name: "参数化执行机名称测试"
@description: "测试执行机名称可以参数化的功能（远程别名变量）"

# 启动/连接三台远程关键字服务器（本地起三个端口做演示）
@remote: "http://127.0.0.1:18271/" as windows
@remote: "http://127.0.0.1:18272/" as linux
@remote: "http://127.0.0.1:18273/" as mac

# 定义执行机名称变量
pk_name = "windows"
another_pk = "linux"


# 测试1: 基本参数化执行机名称（字符串里包含占位符）
temp_path = ${pk_name} | [生成随机数]
[打印], 内容: "参数化执行机生成的随机数: ${temp_path}"

# 测试2: 使用不同的执行机名称
another_path = ${another_pk} | [生成随机数],名称:132
[打印], 内容: "另一个执行机生成的随机数: ${another_path}"

# 测试3: 在循环中使用参数化执行机
executors = ["windows", "linux", "mac"]
for executor in executors do
    loop_path = ${executor} | [生成随机数]
    [打印], 内容: "循环中 ${executor} 生成的随机数: ${loop_path}"
end

# 测试4: 验证生成的随机数不为空
[断言], 条件: "'${temp_path}' != ''", 消息: "生成的随机数应该不为空"
[断言], 条件: "'${another_path}' != ''", 消息: "另一个生成的随机数应该不为空"
