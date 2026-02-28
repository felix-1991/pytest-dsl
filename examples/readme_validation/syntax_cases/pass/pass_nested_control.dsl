@name: "语法正例-嵌套流程"
items = [1, 2, 3]

for item in ${items} do
    if ${item} > 1 do
        [打印], 内容: "gt1"
    else
        [打印], 内容: "le1"
    end
end
