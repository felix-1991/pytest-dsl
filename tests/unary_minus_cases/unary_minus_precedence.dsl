@name: "Unary Minus - Precedence"
@description: "验证一元负号与二元运算优先级"

left = -1 + 2
right = 3 * -2
combo = -1 + 2 * 3

[打印],内容: ${left} 
[断言], 条件: "${left} == 1", 消息: "-1 + 2 应该为 1"
[断言], 条件: "${right} == -6", 消息: "3 * -2 应该为 -6"
[断言], 条件: "${combo} == 5", 消息: "-1 + 2*3 应该为 5"
