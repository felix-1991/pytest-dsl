@name: "pytest-dsl 综合语法确认"
@description: "覆盖常用 DSL 语法：变量、表达式、列表、字典、条件、循环、retry、关键字赋值、动态索引和字符串插值"
@tags: ["syntax", "compatibility", "dynamic-index", "smoke"]

[打印], 内容: "=== 1. 基本类型、算术表达式和布尔表达式 ==="

project = "pytest-dsl"
base = 10
increment = 3
sum_value = base + increment * 2
wrapped_value = (base + increment) * 2
negative_value = -1
mod_value = sum_value % 5
logic_flag = True and not False

[打印], 内容: "project=${project}, sum=${sum_value}, wrapped=${wrapped_value}, negative=${negative_value}, mod=${mod_value}, logic=${logic_flag}"
[断言], 条件: "${sum_value} == 16", 消息: "算术表达式应保持正确"
[断言], 条件: "${wrapped_value} == 26", 消息: "括号表达式应保持正确"
[断言], 条件: "${negative_value} == -1", 消息: "一元负号应保持正确"
[断言], 条件: "${mod_value} == 1", 消息: "模运算应保持正确"
[断言], 条件: "${logic_flag} == True", 消息: "逻辑表达式应保持正确"

[打印], 内容: "=== 2. 列表、字典、下标访问、属性访问和动态索引 ==="

ids = [0, 1, 2]
items = ["苹果", "香蕉", "橙子"]
users = [{"name": "alice", "age": 30}, {"name": "bob", "age": 25}, {"name": "carol", "age": 28}]
profile = {"env": "dev", "owner": "qa", "enabled": True}
keys = ["env", "owner", "enabled"]

idx = 1
first_item = items[0]
selected_item = items[idx]
computed_item = items[idx + 1]
selected_user_name = users[idx].name
selected_user_age = users[idx].age
first_key = keys[0]
env_value = profile[first_key]
nested_placeholder_item = "${items[${idx}]}"

[打印], 内容: "first=${first_item}, selected=${selected_item}, computed=${computed_item}, user=${selected_user_name}/${selected_user_age}, env=${env_value}, nested=${nested_placeholder_item}"
[断言], 条件: "${first_item} == 苹果", 消息: "固定下标访问应正确"
[断言], 条件: "${selected_item} == 香蕉", 消息: "变量下标访问应正确"
[断言], 条件: "${computed_item} == 橙子", 消息: "表达式下标访问应正确"
[断言], 条件: "${selected_user_name} == bob", 消息: "下标后的属性访问应正确"
[断言], 条件: "${selected_user_age} == 25", 消息: "属性访问保留数字类型"
[断言], 条件: "${env_value} == dev", 消息: "字典动态键访问应正确"
[断言], 条件: "${nested_placeholder_item} == 香蕉", 消息: "嵌套占位符动态索引应正确"

[打印], 内容: "=== 3. 关键字赋值、字符串操作和参数内动态索引 ==="

returned_item = [返回结果], 结果: ${items[${idx}]}
upper_project = [字符串操作], 操作: "upper", 字符串: ${project}
split_item = [字符串操作], 操作: "split", 字符串: "red,green,blue", 参数1: ",", 参数2: "1"

[打印], 内容: "returned=${returned_item}, upper=${upper_project}, split=${split_item}"
[断言], 条件: "${returned_item} == 香蕉", 消息: "关键字参数中的嵌套动态索引应正确"
[断言], 条件: "${upper_project} == PYTEST-DSL", 消息: "关键字返回赋值应正确"
[断言], 条件: "${split_item} == green", 消息: "字符串 split 操作应正确"

[打印], 内容: "=== 4. range 循环、数组遍历、字典键值遍历和嵌套循环 ==="

range_trace = ""
for i in range(0, 3) do
    current_id = ids[i]
    current_item = items[i]
    current_user_name = users[i].name
    nested_item = "${items[${i}]}"
    range_trace = "${range_trace}${current_id}:${current_item};"
    [打印], 内容: "range i=${i}, id=${current_id}, item=${current_item}, user=${current_user_name}, nested=${nested_item}"
end

[打印], 内容: "range_trace=${range_trace}"
[断言], 条件: "${range_trace} == 0:苹果;1:香蕉;2:橙子;", 消息: "range 循环和动态索引应正确"

item_trace = ""
for item in items do
    item_trace = "${item_trace}${item}|"
    [打印], 内容: "item loop: ${item}"
end

[打印], 内容: "item_trace=${item_trace}"
[断言], 条件: "${item_trace} == 苹果|香蕉|橙子|", 消息: "列表遍历应正确"

dict_trace = ""
for key, value in profile do
    dict_trace = "${dict_trace}${key}=${value};"
    [打印], 内容: "dict loop: ${key}=${value}"
end

[打印], 内容: "dict_trace=${dict_trace}"

matrix = [[1, 2], [3, 4]]
matrix_sum = 0
for row in matrix do
    for cell in row do
        matrix_sum = matrix_sum + cell
        [打印], 内容: "matrix cell=${cell}, sum=${matrix_sum}"
    end
end

[断言], 条件: "${matrix_sum} == 10", 消息: "嵌套循环和数值累加应正确"

[打印], 内容: "=== 5. if / elif / else、比较、in、not in ==="

branch_result = "unset"
if sum_value > 20 do
    branch_result = "too-large"
elif selected_item in items and "缺失" not in items do
    branch_result = "matched"
else
    branch_result = "fallback"
end

[打印], 内容: "branch_result=${branch_result}"
[断言], 条件: "${branch_result} == matched", 消息: "elif、in、not in 和逻辑表达式应正确"

[打印], 内容: "=== 6. continue / break 循环控制 ==="

control_trace = ""
for n in range(0, 5) do
    if n == 1 do
        [打印], 内容: "continue at n=${n}"
        continue
    end

    if n == 4 do
        [打印], 内容: "break at n=${n}"
        break
    end

    control_trace = "${control_trace}n${n};"
    [打印], 内容: "control n=${n}, trace=${control_trace}"
end

[断言], 条件: "${control_trace} == n0;n2;n3;", 消息: "continue 和 break 应正确"

[打印], 内容: "=== 7. retry 块 ==="

retry_marker = "before"
retry 2 times every 0 until retry_marker == "done" do
    retry_marker = [返回结果], 结果: "done"
    [打印], 内容: "retry marker=${retry_marker}"
end

[断言], 条件: "${retry_marker} == done", 消息: "retry 块应正确执行"

[打印], 内容: "=== 综合语法确认完成 ==="
