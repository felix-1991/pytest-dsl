@name: "retry 块：仅次数"
@description: "演示 retry 2 do 的最简语法"

a = 1
retry 2 do
    [打印],内容: "测试下"
    [断言],条件: "1+1 == 2", 消息: "成功"
end

[打印],内容: "打印不了"
teardown do 
    [打印],内容: "能走到"
end
