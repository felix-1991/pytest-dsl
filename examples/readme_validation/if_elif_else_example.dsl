@name: "if-elif-else语句示例"
@description: "展示if-elif-else语句的各种用法"
@tags: ["示例", "条件语句"]
@author: "pytest-dsl"
@date: 2024-12-19

[打印], 内容: "🚀 if-elif-else语句功能演示"

# 示例1: 成绩评级系统
[打印], 内容: "\n📊 示例1: 成绩评级系统"
score = 85

if score >= 90 do
    grade = "A"
    comment = "优秀"
elif score >= 80 do
    grade = "B"
    comment = "良好"
elif score >= 70 do
    grade = "C"
    comment = "中等"
elif score >= 60 do
    grade = "D"
    comment = "及格"
else
    grade = "F"
    comment = "不及格"
end

[打印], 内容: "分数: ${score}, 等级: ${grade}, 评价: ${comment}"

# 示例2: 用户权限管理
[打印], 内容: "\n👤 示例2: 用户权限管理"
user = {"role": "admin", "level": 3, "active": True}
role = ${user["role"]}
level = ${user["level"]}
active = ${user["active"]}

if active == False do
    permission = "账户已禁用"
elif role == "admin" do
    if level >= 5 do
        permission = "超级管理员"
    elif level >= 3 do
        permission = "高级管理员"
    else
        permission = "普通管理员"
    end
elif role == "moderator" do
    permission = "版主权限"
elif role == "user" do
    permission = "普通用户"
else
    permission = "未知角色"
end

[打印], 内容: "用户角色: ${role}, 权限级别: ${permission}"

# 示例3: 天气建议系统
[打印], 内容: "\n🌤️ 示例3: 天气建议系统"
temperature = 22
humidity = 65
wind_speed = 5

if temperature > 30 do
    if humidity > 70 do
        advice = "天气炎热潮湿，建议待在室内开空调"
    else
        advice = "天气炎热，注意防晒和补水"
    end
elif temperature > 20 do
    if wind_speed > 10 do
        advice = "天气温暖但风大，适合户外活动但注意防风"
    else
        advice = "天气温暖宜人，适合户外活动"
    end
elif temperature > 10 do
    advice = "天气凉爽，建议穿长袖外出"
elif temperature > 0 do
    advice = "天气寒冷，注意保暖"
else
    advice = "天气严寒，尽量减少外出"
end

[打印], 内容: "温度: ${temperature}°C, 湿度: ${humidity}%, 风速: ${wind_speed}m/s"
[打印], 内容: "建议: ${advice}"

# 示例4: 订单状态处理
[打印], 内容: "\n📦 示例4: 订单状态处理"
order_status = "processing"
payment_status = "paid"
shipping_method = "express"

if order_status == "cancelled" do
    message = "订单已取消"
elif order_status == "completed" do
    message = "订单已完成"
elif order_status == "processing" do
    if payment_status == "paid" do
        if shipping_method == "express" do
            message = "订单处理中，将使用快递发货"
        elif shipping_method == "standard" do
            message = "订单处理中，将使用标准配送"
        else
            message = "订单处理中，配送方式待确认"
        end
    elif payment_status == "pending" do
        message = "等待付款确认"
    else
        message = "付款状态异常"
    end
elif order_status == "pending" do
    message = "订单待确认"
else
    message = "未知订单状态"
end

[打印], 内容: "订单状态: ${order_status}, 付款状态: ${payment_status}"
[打印], 内容: "处理结果: ${message}"

[打印], 内容: "\n✅ if-elif-else语句演示完成！"
