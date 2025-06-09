@name: "HTTP工具关键字"
@description: "专门用于HTTP API测试的关键字集合"
@author: "API测试团队"
@date: "2024-01-15"

# 导入基础工具
@import: "../common/utils.resource"

# API相关常量
API_TIMEOUT = 30
RETRY_DELAY = 2

# 认证相关关键字
function 登录获取Token (用户名, 密码, 服务器="default") do
    [打印], 内容: "开始登录用户: ${用户名}"
    
    # 使用导入的格式化消息关键字
    登录消息 = [格式化消息], 模板: "用户登录", 变量值: ${用户名}
    [打印], 内容: ${登录消息}
    
    # 模拟登录过程，简化Token生成
    模拟Token = "token_${用户名}_123456"
    
    [打印], 内容: "登录成功 - Token: ${模拟Token}"
    
    # 返回简化的结果
    return ${模拟Token}
end

function 带认证的API调用 (方法, 路径, 数据="", token="") do
    # 使用导入的验证关键字
    验证结果 = [验证非空], 值: ${方法}, 字段名: "HTTP方法"
    
    # 简化验证结果处理
    if ${验证结果} == "验证失败" do
        [打印], 内容: "API调用失败: HTTP方法不能为空"
        return "API调用失败"
    end
    
    [打印], 内容: "${方法} ${路径} 调用完成"
    
    # 返回简化的结果
    return "API调用成功"
end

# CRUD操作关键字
function 创建资源 (资源类型, 数据="", token="") do
    [打印], 内容: "创建${资源类型}资源"
    
    调用结果 = [带认证的API调用], 方法: "POST", 路径: "/api/${资源类型}", 数据: ${数据}, token: ${token}
    
    return "资源创建完成"
end

function 获取资源 (资源类型, 资源ID, token="") do
    [打印], 内容: "获取${资源类型}资源: ${资源ID}"
    
    调用结果 = [带认证的API调用], 方法: "GET", 路径: "/api/${资源类型}/${资源ID}", token: ${token}
    
    return "资源获取完成"
end 