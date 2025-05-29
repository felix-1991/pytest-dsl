@name: "认证相关关键字"
@description: "处理登录、登出等认证操作"

function 用户登录 (用户名, 密码, 客户端="default") do
    [打印], 内容: "模拟用户登录: ${用户名}"
    
    # 模拟HTTP登录请求
    [HTTP请求], 客户端: ${客户端}, 配置: '''
        method: GET
        url: https://jsonplaceholder.typicode.com/users/1
        captures:
            access_token: ["jsonpath", "$.id"]
            user_id: ["jsonpath", "$.id"]
        asserts:
            - ["status", "eq", 200]
    ''', 步骤名称: "用户登录: ${用户名}"

    # 设置全局token供后续请求使用
    [设置全局变量], 变量名: "auth_token", 值: ${access_token}
    [设置全局变量], 变量名: "current_user_id", 值: ${user_id}

    return ${access_token}
end

function 用户登出 (客户端="default") do
    token = [获取全局变量], 变量名: "auth_token"
    [打印], 内容: "模拟用户登出，token: ${token}"

    # 模拟HTTP登出请求
    [HTTP请求], 客户端: ${客户端}, 配置: '''
        method: GET
        url: https://jsonplaceholder.typicode.com/posts/1
        asserts:
            - ["status", "eq", 200]
    ''', 步骤名称: "用户登出"

    # 清除认证信息
    [设置全局变量], 变量名: "auth_token", 值: ""
    [设置全局变量], 变量名: "current_user_id", 值: ""
end
