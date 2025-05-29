@name: "if-elif-else语句测试"
@description: "测试if-elif-else条件语句的各种用法"
@tags: ["条件语句", "测试"]
@author: "pytest-dsl"
@date: 2024-12-19

# 测试1: 基本的if-elif-else结构
[打印], 内容: "=== 测试1: 基本if-elif-else ==="
score = 85

if score >= 90 do
    [打印], 内容: "优秀 (A)"
elif score >= 80 do
    [打印], 内容: "良好 (B)"
elif score >= 70 do
    [打印], 内容: "中等 (C)"
elif score >= 60 do
    [打印], 内容: "及格 (D)"
else
    [打印], 内容: "不及格 (F)"
end

# 测试2: 多个elif分支
[打印], 内容: "=== 测试2: 多个elif分支 ==="
day = 3

if day == 1 do
    [打印], 内容: "星期一"
elif day == 2 do
    [打印], 内容: "星期二"
elif day == 3 do
    [打印], 内容: "星期三"
elif day == 4 do
    [打印], 内容: "星期四"
elif day == 5 do
    [打印], 内容: "星期五"
elif day == 6 do
    [打印], 内容: "星期六"
elif day == 7 do
    [打印], 内容: "星期日"
else
    [打印], 内容: "无效的日期"
end

# 测试3: 只有if和elif，没有else
[打印], 内容: "=== 测试3: 只有if和elif ==="
temperature = 25

if temperature > 30 do
    [打印], 内容: "天气很热"
elif temperature > 20 do
    [打印], 内容: "天气温暖"
elif temperature > 10 do
    [打印], 内容: "天气凉爽"
end

# 测试4: 嵌套的if-elif-else
[打印], 内容: "=== 测试4: 嵌套条件语句 ==="
age = 25
has_license = True

if age >= 18 do
    [打印], 内容: "成年人"
    if has_license == True do
        [打印], 内容: "可以开车"
    else
        [打印], 内容: "需要考驾照"
    end
elif age >= 16 do
    [打印], 内容: "青少年"
    [打印], 内容: "不能开车"
else
    [打印], 内容: "未成年人"
    [打印], 内容: "不能开车"
end

# 测试5: 复杂条件表达式
[打印], 内容: "=== 测试5: 复杂条件表达式 ==="
x = 15
y = 20

if x > 20 do
    [打印], 内容: "x大于20"
elif x > 10 do
    if y > 15 do
        [打印], 内容: "x在10-20之间，且y大于15"
    else
        [打印], 内容: "x在10-20之间，但y不大于15"
    end
else
    [打印], 内容: "x不大于10"
end

# 测试6: 字符串比较
[打印], 内容: "=== 测试6: 字符串比较 ==="
status = "active"

if status == "active" do
    [打印], 内容: "状态：激活"
elif status == "inactive" do
    [打印], 内容: "状态：未激活"
elif status == "pending" do
    [打印], 内容: "状态：待处理"
else
    [打印], 内容: "状态：未知"
end

[打印], 内容: "=== if-elif-else测试完成 ==="
