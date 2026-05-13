@name: "基本语法示例"
@description: "验证基本语法功能"

# 字符串变量
name = "pytest-dsl"
version = "1.0.0"

# 数字变量
port = 8080

# 列表
users = ["alice", "bob", "charlie"]

# 条件判断
status = "success"
status_message = ""
if status == "success" do
    status_message = "测试通过"
    [打印], 内容: "测试通过"
else
    status_message = "测试失败"
    [打印], 内容: "测试失败"
end

# 循环结构
num = 4
loop_count = 0
for i in range(1, num) do
    loop_count = ${loop_count} + 1
    [打印], 内容: "执行第 ${i} 次"
end

[断言], 条件: "${status_message} == '测试通过'", 消息: "条件判断应进入成功分支"
[断言], 条件: "${loop_count} == 3", 消息: "range(1, 4) 应循环3次"
