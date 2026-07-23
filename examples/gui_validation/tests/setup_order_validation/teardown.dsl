# 兼容旧命名：teardown 中应当最后执行
最终顺序 = [获取全局变量], 变量名: "gui_validation_setup_order"
[断言], 条件: "'${最终顺序.result}' == 'setup->setup_2->setup_10->case->teardown_10->teardown_2'", 消息: "最终teardown顺序不正确"
[打印], 内容: "[顺序验收] 7/7 teardown.dsl，完整流程验证通过"
[打印], 内容: "[顺序验收] 完整顺序=${最终顺序.result}->teardown"
[删除全局变量], 变量名: "gui_validation_setup_order"
