# 增强的变量访问语法

pytest-dsl 现在支持更强大的变量访问语法，类似于 Python 的字典和数组访问方式。

## 支持的语法

### 1. 基本变量访问
```dsl
${variable_name}
```

### 2. 点号访问（对象属性）
```dsl
${object.property}
${nested.object.property}
```

### 3. 数组索引访问
```dsl
${array[0]}          # 第一个元素
${array[1]}          # 第二个元素
${array[-1]}         # 最后一个元素
${array[-2]}         # 倒数第二个元素
```

### 4. 字典键访问
```dsl
${dict["key"]}       # 使用双引号
${dict['key']}       # 使用单引号
${config["api-key"]} # 带连字符的键
```

### 5. 混合访问模式
```dsl
${users[0].name}                    # 数组中对象的属性
${data["users"][0]["name"]}         # 嵌套字典和数组
${config.servers[0].endpoints["api"]} # 复杂嵌套结构
```

## 使用示例

### YAML 配置文件示例
```yaml
# 用户数据
users:
  - id: 1
    name: "张三"
    roles: ["admin", "user"]
    profile:
      email: "zhangsan@example.com"
      settings:
        theme: "dark"
  - id: 2
    name: "李四"
    roles: ["user"]

# 配置映射
config:
  "api-server": "https://api.example.com"
  "timeout": 30

# 嵌套结构
api:
  endpoints:
    login: "/auth/login"
    users: "/api/users"
```

### DSL 测试文件示例
```dsl
@name: "变量访问语法示例"

# 基本访问
[打印], 内容: "第一个用户: ${users[0].name}"

# 数组访问
first_role = ${users[0].roles[0]}
[打印], 内容: "第一个角色: ${first_role}"

# 字典键访问
api_server = ${config["api-server"]}
[打印], 内容: "API服务器: ${api_server}"

# 复杂嵌套访问
user_theme = ${users[0].profile.settings.theme}
[打印], 内容: "用户主题: ${user_theme}"

# 在字符串中使用
[打印], 内容: "用户${users[0].name}的邮箱是${users[0].profile.email}"
```

## 错误处理

当访问不存在的变量、索引或键时，系统会抛出详细的错误信息：

- **变量不存在**: `变量 'nonexistent' 不存在`
- **数组索引超出范围**: `数组索引 10 超出范围，数组长度为 3`
- **字典键不存在**: `字典中不存在键 'nonexistent'`
- **类型错误**: `无法在 str 类型上使用索引访问`

## 向后兼容性

新的语法完全向后兼容，现有的点号访问语法继续正常工作：

```dsl
# 这些语法仍然有效
${api.base_url}
${user.profile.name}
${config.timeout}
```

## 性能说明

- 新的变量解析器优先使用高效的路径解析
- 如果新解析器失败，会自动回退到旧的解析逻辑
- 变量查找优先级：本地变量 > 测试上下文 > YAML变量 > 全局上下文

## 最佳实践

1. **使用描述性的变量名**
   ```dsl
   admin_user = ${users[0].name}
   api_endpoint = ${config["api-server"]}
   ```

2. **避免过深的嵌套**
   ```dsl
   # 推荐：分步访问
   first_user = ${users[0]}
   user_email = ${first_user.profile.email}
   
   # 不推荐：过深嵌套
   email = ${data.users.list[0].profile.contact.email.primary}
   ```

3. **使用适当的引号**
   ```dsl
   # 对于包含特殊字符的键，使用引号
   ${config["api-key"]}
   ${servers["dev-server"]}
   ```

4. **错误处理**
   ```dsl
   # 在使用前确保数据存在
   user_count = ${users.length}
   [断言], 条件: "${user_count} > 0", 消息: "用户列表不能为空"
   first_user = ${users[0].name}
   ```
