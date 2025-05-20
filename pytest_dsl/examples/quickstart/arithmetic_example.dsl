@name: "算术运算示例"
@description: "测试基本的算术运算功能"
@tags: ["arithmetic", "math"]
@author: "System"
@date: 2023-09-01

# 基本运算
a = 10
b = 5
sum = a + b
difference = a - b
product = a * b
quotient = a / b

# 输出结果
[打印],内容: "a = ${a}, b = ${b}"
[打印],内容: "加法: ${a} + ${b} = ${sum}"
[打印],内容: "减法: ${a} - ${b} = ${difference}"
[打印],内容: "乘法: ${a} * ${b} = ${product}"
[打印],内容: "除法: ${a} / ${b} = ${quotient}"

# 混合运算和优先级
result1 = a + b * 2
[打印],内容: "不使用括号: ${a} + ${b} * 2 = ${result1}"

result2 = (a + b) * 2
[打印],内容: "使用括号: (${a} + ${b}) * 2 = ${result2}"

# 字符串操作
name = "测试"
greeting = "你好, " + name
[打印],内容: ${greeting}

# 字符串重复
stars = "*" * 10
[打印],内容: ${stars}

# 复杂表达式
complex_result = (a + b) * (a - b) / 5
[打印],内容: "复杂表达式: (${a} + ${b}) * (${a} - ${b}) / 5 = ${complex_result}"

# 在条件语句中使用
if a + b > a * b do
    [打印],内容: "a + b 大于 a * b"
else
    [打印],内容: "a + b 小于等于 a * b"
end

# 在循环中使用
for i in range(1, 5) do
    squared = i * i
    [打印],内容: "${i} 的平方是 ${squared}"
end 