当前顺序 = [获取全局变量], 变量名: "gui_validation_setup_order"
[断言], 条件: "'${当前顺序.result}' == 'setup->setup_2->setup_10->case'", 消息: "teardown_10 执行前的顺序不正确"
[设置全局变量], 变量名: "gui_validation_setup_order", 值: "${当前顺序.result}->teardown_10"
[打印], 内容: "[顺序验收] 5/7 teardown_10_database.dsl，当前顺序=${当前顺序.result}->teardown_10"
