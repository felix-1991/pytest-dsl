@name: "表达式优先级与 retry 验收"
@description: "覆盖不带括号的算术比较在 retry、if、赋值和占位符插值中的执行行为"

base_count = 105
enabled_count = 100
retry_hits = 0

retry 10 every 0 until enabled_count == base_count + 1 do
    enabled_count = enabled_count + 1
    retry_hits = retry_hits + 1
end

[断言], 条件: "${enabled_count} == 106", 消息: "retry until 应支持右侧裸算术表达式"
[断言], 条件: "${retry_hits} == 6", 消息: "retry 不应在第一次执行后提前退出"

left_operand_ok = False
if 5 + 5 > 8 do
    left_operand_ok = True
end

right_operand_ok = False
if 8 < 5 + 5 do
    right_operand_ok = True
end

mixed_precedence_ok = False
if 10 + 5 * 2 == 20 do
    mixed_precedence_ok = True
end

division_modulo_ok = False
if 20 / 4 == 5 and 10 % 3 == 1 do
    division_modulo_ok = True
end

logic_ok = False
if True and 1 + 1 == 2 do
    logic_ok = True
end

assignment_value = base_count + 1
interpolated_value = "value=${base_count + 1}"

[断言], 条件: "${left_operand_ok} == True", 消息: "比较左侧应支持裸算术表达式"
[断言], 条件: "${right_operand_ok} == True", 消息: "比较右侧应支持裸算术表达式"
[断言], 条件: "${mixed_precedence_ok} == True", 消息: "算术优先级应高于比较"
[断言], 条件: "${division_modulo_ok} == True", 消息: "乘除模优先级应高于比较"
[断言], 条件: "${logic_ok} == True", 消息: "逻辑表达式应正确组合算术比较"
[断言], 条件: "${assignment_value} == 106", 消息: "赋值表达式应保持算术语义"
[断言], 条件: "${interpolated_value} == 'value=106'", 消息: "占位符插值应支持裸算术表达式"
