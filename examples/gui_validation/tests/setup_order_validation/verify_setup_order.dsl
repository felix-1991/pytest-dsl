@name: "多文件 setup 数字顺序验收"
@description: "验证 setup.dsl 最先、编号 setup 按数值升序、teardown 按相反顺序执行"
@tags: ["gui-validation", "setup", "order"]

当前顺序 = [获取全局变量], 变量名: "gui_validation_setup_order"
[打印], 内容: "[顺序验收] 4/7 测试用例，setup执行结果=${当前顺序.result}"
[断言], 条件: "'${当前顺序.result}' == 'setup->setup_2->setup_10'", 消息: "多文件setup未按预期的数字顺序执行"
[设置全局变量], 变量名: "gui_validation_setup_order", 值: "${当前顺序.result}->case"

[打印], 内容: "[顺序验收] setup顺序验证通过，接下来应看到 teardown_10、teardown_2、teardown.dsl"
