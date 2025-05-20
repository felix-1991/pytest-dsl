@name: "简单算术运算"
@description: "简单的算术运算验证示例"
@tags: ["arithmetic"]
@author: "System"
@date: 2023-09-01

# 整数运算
a = 10
b = 3

# 基本四则运算
sum = a + b
difference = a - b
product = a * b
division = a / b

[打印],内容: "基本四则运算"
[打印],内容: "${a} + ${b} = ${sum}"
[打印],内容: "${a} - ${b} = ${difference}"
[打印],内容: "${a} * ${b} = ${product}"
[打印],内容: "${a} / ${b} = ${division}"

# 括号和复合运算
exp1 = a + b * 2
exp2 = (a + b) * 2
exp3 = (a + b) * (a - b)

[打印],内容: "复合运算"
[打印],内容: "a + b * 2 = ${exp1}"
[打印],内容: "(a + b) * 2 = ${exp2}"
[打印],内容: "(a + b) * (a - b) = ${exp3}" 