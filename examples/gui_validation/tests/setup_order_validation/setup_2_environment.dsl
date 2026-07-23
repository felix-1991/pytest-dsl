# 数字 2 应当排在数字 10 之前，而不是按文件名字典序排列
当前顺序 = [获取全局变量], 变量名: "gui_validation_setup_order"
[断言], 条件: "'${当前顺序.result}' == 'setup'", 消息: "setup_2 执行前的顺序不正确"
[设置全局变量], 变量名: "gui_validation_setup_order", 值: "${当前顺序.result}->setup_2"
[打印], 内容: "[顺序验收] 2/7 setup_2_environment.dsl，当前顺序=${当前顺序.result}->setup_2"
