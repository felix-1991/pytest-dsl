@name: "If-Else示例测试"
@description: "测试if-else逻辑分支功能"
@tags: ["if-else", "conditional"]
@author: System
@date: 2023-08-15

# 设置变量
x = 10
y = 5

# 使用if语句判断条件
if x > y do
    result1 = "x大于y，条件为真"
    [打印],内容: ${result1}
end

# 变量赋值使得条件为假
y = 20

# 使用if-else语句判断条件
if x > y do
    result2 = "这不应该执行到，条件为假"
    [打印],内容: ${result2}
else
    result2 = "条件为假，执行else分支"
    [打印],内容: ${result2}
end

# 使用嵌套if-else
value = 7

if value > 10 do
    if value < 20 do
        result3 = "value在10和20之间"
        [打印],内容: ${result3}
    else
        result3 = "value大于等于20"
        [打印],内容: ${result3}
    end
else
    result3 = "value小于等于10"
    [打印],内容: result3
end 