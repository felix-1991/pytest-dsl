@name: "新for循环语法示例"
@description: "展示数组遍历和字典遍历的新语法"
@tags: ["语法示例", "for循环"]

# 数组遍历示例
colors = ["红", "绿", "蓝"]
color_count = 0
last_color = ""
[打印], 内容: "颜色列表遍历："

for color in colors do
    color_count = ${color_count} + 1
    last_color = "${color}"
    [打印], 内容: "颜色: ${color}"
end

# 字典遍历示例
person = {
    "姓名": "李明",
    "年龄": 28,
    "职业": "程序员"
}

info_count = 0
[打印], 内容: "个人信息遍历："

for key, value in person do
    info_count = ${info_count} + 1
    [打印], 内容: "${key}: ${value}"
end

# 传统range循环（仍然支持）
[打印], 内容: "传统range循环："

range_sum = 0
for i in range(1, 4) do
    range_sum = ${range_sum} + ${i}
    [打印], 内容: "第${i}次"
end

[断言], 条件: "${color_count} == 3", 消息: "数组遍历应执行3次"
[断言], 条件: "${last_color} == '蓝'", 消息: "数组遍历最后一个元素应为蓝"
[断言], 条件: "${info_count} == 3", 消息: "字典遍历应执行3次"
[断言], 条件: "${range_sum} == 6", 消息: "range循环累加结果应为6"
