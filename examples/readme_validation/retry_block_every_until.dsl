@name: "retry 块：次数 + 间隔 + 条件"
@description: "演示 retry 5 every 2 until ... do 的语法"

status = "pending"

a = 1
retry 5 every 2 until ${status} == "ready" do
    [打印], 内容: "检查状态..."
    if a == 2 do
        status = "ready"
    end 
    a = a + 1
end
