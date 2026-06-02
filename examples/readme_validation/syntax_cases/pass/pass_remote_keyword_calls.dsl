@name: "语法正例-远程关键字调用"
@remote: "http://localhost:8270/" as remote_server
@remote: "http://${host}:${port}/" as ${dynamic_alias}

item_id = 1

remote_server|[无参关键字]
remote_server|[打印], 内容: "远程有参调用", 次数: 1

direct_result = remote_server|[返回结果], 结果: "ok"
dynamic_result = ${dynamic_alias}|[fetch], id: item_id + 1

retry 2 every 0 until direct_result == "ok" do
    remote_server|[打印], 内容: "retry 内远程调用"
end

teardown do
    ${dynamic_alias}|[清理], 状态: "done"
end
