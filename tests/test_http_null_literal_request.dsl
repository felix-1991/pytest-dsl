@name: "HTTP请求null字面量验证"
@description: "验证DSL null字面量注入HTTP JSON请求体时保持为JSON null"
@tags: [HTTP, "null"]

caller = null

request_result = [HTTP请求], 客户端: "default", 配置: """
method: POST
url: https://example.test/async-task
request:
  headers:
    Content-Type: application/json
  json:
    asyncWaitTime: 3000
    meta:
      caller: ${caller}
      operator: system
    taskID: task-20250408-005
    tasks:
      - action: fileQuarantine
        type: file
        id: task_process_001
        file:
          name: fileQuarantine.exe
          path: C:\\Users\\tester\\Desktop\\fileQuarantine.exe
          md5: 0123456789abcdef0123456789abcdef
          size: 102400
        virus:
          virusName: Trojan.Win32.Generic
          virusType: 1
          riskLevel: 3
asserts:
  - ["status", "eq", 200]
"""
