@name: "变量访问语法示例"

# 基本变量访问
simple_var = "test_value"
[打印], 内容: "基本变量: ${simple_var}"

# 使用YAML配置中的嵌套变量
[打印], 内容: "当前环境: ${environment}"
[打印], 内容: "API地址: ${api.base_url}"

# 嵌套访问（使用YAML中的test_users）
admin_user = ${test_users.admin.username}
admin_pass = ${test_users.admin.password}
[打印], 内容: "管理员用户: ${admin_user}"
[打印], 内容: "管理员密码: ${admin_pass}"

# 在字符串中使用变量
[打印], 内容: "用户${test_users.admin.username}的密码是${test_users.admin.password}"
