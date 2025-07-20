@name: "新for循环语法示例"
@description: "展示数组遍历和字典遍历的新语法"
@tags: ["语法示例", "for循环"]

# 数组遍历示例
colors = ["红", "绿", "蓝"]
[打印], 内容: "颜色列表遍历："

for color in colors do
    [打印], 内容: "颜色: ${color}"
end

# 字典遍历示例
person = {
    "姓名": "李明",
    "年龄": 28,
    "职业": "程序员"
}

[打印], 内容: "个人信息遍历："

for key, value in person do
    [打印], 内容: "${key}: ${value}"
end

# 传统range循环（仍然支持）
[打印], 内容: "传统range循环："

for i in range(1, 4) do
    [打印], 内容: "第${i}次"
end 