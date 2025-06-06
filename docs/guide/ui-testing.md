# Web UI 测试

pytest-dsl 通过 `pytest-dsl-ui` 扩展包提供了强大的Web UI自动化测试能力，支持各种浏览器操作和界面交互测试。

## 安装

```bash
# 安装UI测试扩展包
pip install pytest-dsl-ui

# 或使用uv（推荐）
uv pip install pytest-dsl-ui
```

安装后，你可以在DSL测试文件中直接使用所有UI相关的关键字。

## 浏览器管理

### 打开浏览器

```python
# 打开Chrome浏览器（默认）
[打开浏览器]

# 指定浏览器类型
[打开浏览器], 浏览器类型: "firefox"

# 启用无头模式
[打开浏览器], 浏览器类型: "chrome", 无头模式: true

# 设置窗口大小
[打开浏览器], 浏览器类型: "chrome", 窗口大小: "1920x1080"

# 设置用户数据目录
[打开浏览器], 浏览器类型: "chrome", 用户数据目录: "/path/to/profile"
```

### 关闭浏览器

```python
# 关闭当前浏览器
[关闭浏览器]

# 关闭所有浏览器实例
[关闭所有浏览器]
```

## 页面导航

### 访问页面

```python
# 访问指定URL
[访问页面], URL: "https://example.com"

# 等待页面加载完成
[访问页面], URL: "https://example.com", 超时时间: 30
```

### 页面操作

```python
# 页面刷新
[刷新页面]

# 返回上一页
[返回上一页]

# 前进到下一页
[前进到下一页]

# 获取当前页面URL
current_url = [获取当前URL]

# 获取页面标题
page_title = [获取页面标题]
```

## 元素操作

### 元素查找

支持多种选择器类型：

```python
# CSS选择器
[点击元素], 选择器: "#submit-button"
[点击元素], 选择器: ".login-form input[type='submit']"

# XPath选择器
[点击元素], 选择器: "//button[@id='submit']", 选择器类型: "xpath"

# 文本内容查找
[点击元素], 选择器: "登录", 选择器类型: "text"

# 部分文本匹配
[点击元素], 选择器: "提交", 选择器类型: "partial_text"
```

### 元素交互

```python
# 点击元素
[点击元素], 选择器: "#login-button"

# 双击元素
[双击元素], 选择器: "#file-item"

# 右键点击
[右键点击元素], 选择器: "#context-menu-target"

# 悬停在元素上
[悬停元素], 选择器: ".tooltip-trigger"

# 输入文本
[输入文本], 选择器: "input[name='username']", 文本: "admin"

# 清空输入框
[清空文本], 选择器: "input[name='search']"

# 选择下拉选项
[选择选项], 选择器: "select[name='country']", 选项值: "china"
[选择选项], 选择器: "select[name='country']", 选项文本: "中国"

# 上传文件
[上传文件], 选择器: "input[type='file']", 文件路径: "/path/to/file.jpg"
```

### 表单操作

```python
# 勾选复选框
[勾选复选框], 选择器: "input[name='agree']"

# 取消勾选复选框
[取消勾选复选框], 选择器: "input[name='newsletter']"

# 选择单选按钮
[选择单选按钮], 选择器: "input[name='gender'][value='male']"

# 提交表单
[提交表单], 选择器: "#login-form"
```

## 等待和断言

### 等待元素

```python
# 等待元素出现
[等待元素出现], 选择器: "#loading-complete", 超时时间: 10

# 等待元素消失
[等待元素消失], 选择器: ".loading-spinner", 超时时间: 15

# 等待元素可点击
[等待元素可点击], 选择器: "#submit-button", 超时时间: 5

# 等待元素包含文本
[等待元素包含文本], 选择器: ".status", 期望文本: "成功", 超时时间: 10
```

### 元素断言

```python
# 断言元素存在
[断言元素存在], 选择器: "#welcome-message"

# 断言元素不存在
[断言元素不存在], 选择器: ".error-message"

# 断言元素可见
[断言元素可见], 选择器: "#main-content"

# 断言元素隐藏
[断言元素隐藏], 选择器: "#hidden-panel"

# 断言元素文本
[断言元素文本], 选择器: ".welcome", 期望文本: "欢迎回来"

# 断言元素包含文本
[断言元素包含文本], 选择器: ".status", 期望文本: "成功"

# 断言元素属性
[断言元素属性], 选择器: "input[name='email']", 属性名: "placeholder", 期望值: "请输入邮箱"

# 断言元素CSS属性
[断言元素样式], 选择器: ".highlight", 样式属性: "color", 期望值: "rgb(255, 0, 0)"
```

## 窗口和标签页管理

```python
# 打开新标签页
[打开新标签页], URL: "https://another-site.com"

# 切换到标签页
[切换到标签页], 索引: 1  # 切换到第二个标签页
[切换到标签页], 标题: "新页面标题"  # 根据标题切换

# 关闭当前标签页
[关闭当前标签页]

# 关闭指定标签页
[关闭标签页], 索引: 2

# 获取所有标签页
tabs = [获取所有标签页]
```

## 屏幕截图和调试

```python
# 截取整个页面
[截取页面截图], 文件路径: "screenshot.png"

# 截取指定元素
[截取元素截图], 选择器: "#main-content", 文件路径: "element.png"

# 获取页面源代码
page_source = [获取页面源代码]

# 执行JavaScript代码
result = [执行JavaScript], 代码: "return document.title;"

# 设置窗口大小
[设置窗口大小], 宽度: 1366, 高度: 768

# 最大化窗口
[最大化窗口]

# 最小化窗口
[最小化窗口]
```

## 高级功能

### Cookie管理

```python
# 设置Cookie
[设置Cookie], 名称: "session_id", 值: "abc123", 域名: "example.com"

# 获取Cookie
cookie_value = [获取Cookie], 名称: "session_id"

# 删除Cookie
[删除Cookie], 名称: "temp_data"

# 清除所有Cookie
[清除所有Cookie]
```

### 本地存储

```python
# 设置本地存储
[设置本地存储], 键: "user_preferences", 值: '{"theme": "dark"}'

# 获取本地存储
preferences = [获取本地存储], 键: "user_preferences"

# 删除本地存储
[删除本地存储], 键: "temp_data"

# 清除本地存储
[清除本地存储]
```

### 警告框处理

```python
# 接受警告框
[接受警告框]

# 取消警告框
[取消警告框]

# 在警告框中输入文本
[警告框输入文本], 文本: "确认操作"

# 获取警告框文本
alert_text = [获取警告框文本]
```

## 配置选项

你可以通过配置文件自定义浏览器行为：

```yaml
# pytest-dsl.yaml
ui:
  default_browser: "chrome"
  headless: false
  window_size: "1920x1080"
  implicit_wait: 10
  page_load_timeout: 30
  script_timeout: 30
  
  # Chrome特定选项
  chrome_options:
    - "--disable-web-security"
    - "--allow-running-insecure-content"
    
  # Firefox特定选项
  firefox_options:
    - "--width=1920"
    - "--height=1080"
```

## 实际应用示例

### 登录测试

```python
@name: "用户登录测试"
@description: "测试用户登录功能"

# 打开浏览器并访问登录页面
[打开浏览器], 浏览器类型: "chrome"
[访问页面], URL: "https://example.com/login"

# 等待页面加载
[等待元素出现], 选择器: "#login-form"

# 输入用户名和密码
[输入文本], 选择器: "input[name='username']", 文本: "testuser"
[输入文本], 选择器: "input[name='password']", 文本: "password123"

# 点击登录按钮
[点击元素], 选择器: "#login-button"

# 等待登录成功
[等待元素出现], 选择器: ".welcome-message", 超时时间: 10

# 验证登录成功
[断言元素包含文本], 选择器: ".welcome-message", 期望文本: "欢迎"
[断言当前URL包含], 期望文本: "/dashboard"

# 清理：关闭浏览器
teardown do
    [关闭浏览器]
end
```

### 表单填写测试

```python
@name: "联系表单测试"
@data: "contact_forms.csv" using csv

[打开浏览器]
[访问页面], URL: "https://example.com/contact"

# 填写表单
[输入文本], 选择器: "input[name='name']", 文本: "${name}"
[输入文本], 选择器: "input[name='email']", 文本: "${email}"
[选择选项], 选择器: "select[name='subject']", 选项文本: "${subject}"
[输入文本], 选择器: "textarea[name='message']", 文本: "${message}"

# 上传文件（如果需要）
if "${attachment}" != "" do
    [上传文件], 选择器: "input[type='file']", 文件路径: "${attachment}"
end

# 勾选同意条款
[勾选复选框], 选择器: "input[name='agree_terms']"

# 提交表单
[点击元素], 选择器: "#submit-button"

# 验证提交成功
[等待元素出现], 选择器: ".success-message", 超时时间: 15
[断言元素包含文本], 选择器: ".success-message", 期望文本: "感谢您的留言"

teardown do
    [关闭浏览器]
end
```

## 最佳实践

### 1. 使用显式等待

```python
# 好的做法：使用显式等待
[等待元素出现], 选择器: "#dynamic-content", 超时时间: 10
[点击元素], 选择器: "#dynamic-content button"

# 避免：使用固定延时
# [休眠], 时间: 5  # 不推荐
```

### 2. 优化选择器

```python
# 好的做法：使用稳定的选择器
[点击元素], 选择器: "[data-testid='submit-button']"
[点击元素], 选择器: "#unique-submit-button"

# 避免：使用脆弱的选择器
# [点击元素], 选择器: "body > div:nth-child(3) > button"  # 不推荐
```

### 3. 适当的错误处理

```python
# 使用条件判断处理可选元素
if [元素是否存在], 选择器: ".close-popup" do
    [点击元素], 选择器: ".close-popup"
end

# 继续主要测试流程
[输入文本], 选择器: "#search-input", 文本: "pytest-dsl"
```

### 4. 资源清理

```python
# 在teardown中确保清理资源
teardown do
    [截取页面截图], 文件路径: "final_state.png"
    [关闭浏览器]
end
```

通过这些UI测试关键字，你可以轻松创建强大的Web应用自动化测试，无需深入了解Selenium等底层工具的复杂API。 