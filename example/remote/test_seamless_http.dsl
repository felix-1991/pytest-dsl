# 测试无缝变量传递的HTTP请求功能
# 这个测试验证远程关键字能够无缝使用客户端的YAML配置

# 导入远程服务器（假设服务器已启动）
@remote: "http://localhost:8270/" as test_server

# 测试1：使用客户端的HTTP客户端配置
print "=== 测试1：无缝使用客户端HTTP配置 ==="
test_server|[HTTP请求], 客户端: "default", 配置: '''
request:
  method: GET
  url: ${g_base_url}/api/test
  headers:
    X-Test-User: ${test_data.username}
    X-Test-Email: ${test_data.email}
captures:
  status_code: response.status_code
  response_text: response.text
'''

print "HTTP请求状态码: ${status_code}"
print "响应内容: ${response_text}"

# 测试2：使用全局变量
print "=== 测试2：使用全局变量 ==="
test_server|[HTTP请求], 客户端: "default", 配置: '''
request:
  method: GET
  url: ${g_api_endpoint}/health
captures:
  health_status: response.json.status
'''

print "健康检查状态: ${health_status}"

# 测试3：验证敏感信息不会被传递
print "=== 测试3：验证敏感信息隔离 ==="
# 这个测试应该失败，因为password不应该被同步
try:
    test_server|[打印], 内容: "密码: ${password}"
except Exception as e:
    print "✓ 敏感信息正确隔离: ${e}"

print "=== 无缝变量传递测试完成 ==="
