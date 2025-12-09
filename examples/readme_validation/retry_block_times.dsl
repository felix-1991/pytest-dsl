@name: "retry 块：times + every"
@description: "演示 retry 3 times every 1 do 的语法"

retry 3 times every 1 do
    [打印], 内容: "带 times 修饰词的重试"
end
