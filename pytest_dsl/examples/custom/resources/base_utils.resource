@name: 基础工具关键字
@description: 包含最基础的工具关键字
@author: Felix
@date: 2024-06-11

function 格式化消息 (消息模板, 变量="aaaaaaaaa") do
    [打印],内容:'格式化消息，模板: ${消息模板}, 变量: ${变量}'
    结果 = "${消息模板}: ${变量}"
    [打印],内容:'格式化结果: ${结果}'
    return ${结果}
end