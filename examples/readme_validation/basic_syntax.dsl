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
if status == "success" do
    [打印], 内容: "测试通过"
else
    [打印], 内容: "测试失败"
end

# 循环结构
num = 4
for i in range(1, num) do
    [打印], 内容: "执行第 ${i} 次"
end
