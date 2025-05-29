@name: "使用环境配置"

# 直接使用YAML中的变量
[打印], 内容: "当前环境: ${environment}"
[打印], 内容: "API地址: ${api.base_url}"

# 使用嵌套配置（支持增强的变量访问语法）
admin_user = ${test_users.admin.username}
admin_pass = ${test_users.admin.password}

[打印], 内容: "管理员用户: ${admin_user}"
[打印], 内容: "管理员密码: ${admin_pass}"

# 使用配置进行HTTP请求
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api.base_url}/posts/1
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "使用配置的API地址"
