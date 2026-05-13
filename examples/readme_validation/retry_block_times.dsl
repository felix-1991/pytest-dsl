@name: "retry 块：times + every"
@description: "演示 retry 3 times every 0 until ... do 的语法"

retry_count = 0
retry 3 times every 0 until ${retry_count} == 3 do
    retry_count = ${retry_count} + 1
    [打印], 内容: "带 times 修饰词的重试"
end

[断言], 条件: "${retry_count} == 3", 消息: "retry 3 times 应在until满足前最多执行3次"
