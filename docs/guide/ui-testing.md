# Web UI 测试

pytest-dsl 通过 `pytest-dsl-ui` 扩展包提供了强大的Web UI自动化测试能力，支持各种浏览器操作和界面交互测试。基于Playwright引擎，支持Chromium、Firefox和Webkit浏览器。

## 安装

```bash
# 安装UI测试扩展包
pip install pytest-dsl-ui

# 或使用uv（推荐）
uv pip install pytest-dsl-ui
```

安装后，你可以在DSL测试文件中直接使用所有UI相关的关键字。

## 浏览器管理

### 启动浏览器

```python
# 启动Chromium浏览器（默认）
[启动浏览器]

# 指定浏览器类型
[启动浏览器], 浏览器: "firefox"

# 启用无头模式
[启动浏览器], 浏览器: "chromium", 无头模式: True

# 设置视口大小
[启动浏览器], 浏览器: "chromium", 视口宽度: 1920, 视口高度: 1080

# 设置慢动作模式（用于调试）
[启动浏览器], 浏览器: "chromium", 慢动作: 1000

# 忽略HTTPS证书错误
[启动浏览器], 浏览器: "chromium", 忽略证书错误: True

# 使用配置文件启动
[启动浏览器], 浏览器: "chromium", 配置: """
args:
  - "--start-maximized"
  - "--disable-extensions"
"""
```

### 关闭浏览器

```python
# 关闭当前浏览器
[关闭浏览器]

# 关闭指定浏览器
[关闭浏览器], 浏览器ID: "browser_1"
```

## 页面导航

### 打开页面

```python
# 打开指定URL
[打开页面], 地址: "https://example.com"

# 等待页面加载完成
[打开页面], 地址: "https://example.com", 超时时间: 30

# 指定等待条件
[打开页面], 地址: "https://example.com", 等待条件: "networkidle"
```

### 页面操作

```python
# 页面刷新
[刷新页面]

# 浏览器后退
[后退]

# 浏览器前进
[前进]

# 获取当前页面地址
current_url = [获取当前地址]

# 获取页面标题
page_title = [获取页面标题]
```

## 元素操作

### 元素查找

支持多种定位器类型：

```python
# CSS选择器（默认）
[点击元素], 定位器: "#submit-button"
[点击元素], 定位器: ".login-form input[type='submit']"

# XPath选择器
[点击元素], 定位器: "//button[@id='submit']"

# 文本内容查找
[点击元素], 定位器: "登录"

# 部分文本匹配
[点击元素], 定位器: "提交"
```

### 元素交互

```python
# 点击元素
[点击元素], 定位器: "#login-button"

# 双击元素
[双击元素], 定位器: "#file-item"

# 右键点击
[右键点击元素], 定位器: "#context-menu-target"

# 悬停在元素上
[悬停元素], 定位器: ".tooltip-trigger"

# 输入文本
[输入文本], 定位器: "input[name='username']", 文本: "admin"

# 清空输入框
[清空文本], 定位器: "input[name='search']"

# 选择下拉选项
[选择选项], 定位器: "select[name='country']", 值: "china"
[选择选项], 定位器: "select[name='country']", 标签: "中国"
[选择选项], 定位器: "select[name='country']", 索引: 0

# 上传文件
[上传文件], 定位器: "input[type='file']", 文件路径: "/path/to/file.jpg"
```

### 表单操作

```python
# 勾选复选框
[勾选复选框], 定位器: "input[name='agree']"

# 取消勾选复选框
[取消勾选复选框], 定位器: "input[name='newsletter']"

# 设置复选框状态
[设置复选框状态], 定位器: "input[name='agree']", 选中状态: True

# 选择单选框
[选择单选框], 定位器: "input[name='gender'][value='male']"

# 选择下拉选项（高级）
[选择下拉选项], 定位器: "select[name='category']", 选项值: "technology"
[选择下拉选项], 定位器: "select[name='category']", 选项标签: "科技"
[选择下拉选项], 定位器: "select[name='category']", 选项索引: 2
[选择下拉选项], 定位器: "select[name='tags']", 选项值: "tag1,tag2", 多选: True
```

## 等待和断言

### 等待元素

```python
# 等待元素出现
[等待元素出现], 定位器: "#loading-complete", 状态: "visible", 超时时间: 10

# 等待元素消失
[等待元素出现], 定位器: ".loading-spinner", 状态: "hidden", 超时时间: 15

# 等待元素附加到DOM
[等待元素出现], 定位器: "#submit-button", 状态: "attached", 超时时间: 5

# 等待文本出现
[等待文本出现], 文本: "加载完成", 超时时间: 10

# 设置等待超时时间
[设置等待超时], 超时时间: 30
```

### 元素断言

```python
# 断言元素存在
[断言元素存在], 定位器: "#welcome-message"

# 断言元素可见
[断言元素可见], 定位器: "#main-content"

# 断言元素隐藏
[断言元素隐藏], 定位器: "#hidden-panel"

# 断言元素启用
[断言元素启用], 定位器: "#submit-button"

# 断言元素禁用
[断言元素禁用], 定位器: "#disabled-button"

# 断言元素文本内容
[断言文本内容], 定位器: ".welcome", 期望文本: "欢迎回来"

# 断言元素包含文本
[断言文本内容], 定位器: ".status", 期望文本: "成功", 匹配方式: "contains"

# 断言元素属性值
[断言属性值], 定位器: "input[name='email']", 属性名: "placeholder", 期望值: "请输入邮箱"

# 断言输入值
[断言输入值], 定位器: "input[name='username']", 期望值: "admin"

# 断言复选框状态
[断言复选框状态], 定位器: "input[name='agree']", 期望状态: True

# 断言元素数量
[断言元素数量], 定位器: ".list-item", 期望数量: 5

# 断言页面标题
[断言页面标题], 期望标题: "首页", 匹配方式: "exact"

# 断言页面URL
[断言页面URL], 期望URL: "/dashboard", 匹配方式: "contains"
```

## 页面管理

```python
# 新建页面
[新建页面]

# 切换页面
[切换页面], 页面ID: "page_1"

# 切换到最新页面
[切换到最新页面], 变量名: "latest_page_id"

# 等待新页面出现
[等待新页面], 超时时间: 30, 变量名: "new_page_id"

# 获取页面列表
[获取页面列表], 变量名: "all_pages"

# 根据URL查找页面
[根据URL查找页面], URL: "/dashboard", 精确匹配: False, 变量名: "dashboard_page"

# 根据标题查找页面
[根据标题查找页面], 标题: "首页", 精确匹配: True, 变量名: "home_page"
```

## 屏幕截图和调试

```python
# 截取整个页面
[截图], 文件名: "screenshot.png"

# 截取指定元素
[截图], 元素定位器: "#main-content", 文件名: "element.png"

# 全页面截图
[截图], 文件名: "fullpage.png", 全页面: True

# 执行JavaScript代码
[执行JavaScript], 脚本: "return document.title;", 变量名: "page_title"

# 设置视口大小
[设置视口大小], 宽度: 1366, 高度: 768

# 获取视口大小
[获取视口大小], 变量名: "viewport_size"
```

## 高级功能

### 网络监听

```python
# 开始网络监听
[开始网络监听], 变量名: "network_listener"

# 等待网络请求
[等待网络请求], URL模式: ".*api/users.*", 超时时间: 10, 变量名: "user_request"

# 等待网络响应
[等待网络响应], URL模式: ".*api/users.*", 状态码: 200, 超时时间: 10, 变量名: "user_response"

# 获取网络请求
[获取网络请求], URL模式: ".*api.*", 变量名: "api_requests"

# 获取网络响应
[获取网络响应], URL模式: ".*api.*", 变量名: "api_responses"

# 停止网络监听
[停止网络监听]
```

### 录制功能

```python
# 开始录制
[开始录制], 文件名: "test_recording.webm", 变量名: "recording_path"

# 停止录制
[停止录制], 变量名: "final_recording_path"
```

### 下载管理

```python
# 等待下载
[等待下载], 触发元素: "#download-button", 保存路径: "/downloads/file.pdf", 超时时间: 30, 变量名: "download_path"

# 监听下载
[监听下载], 监听时间: 10, 保存目录: "/downloads", 变量名: "downloaded_files"

# 验证下载文件
[验证下载文件], 文件路径: "/downloads/report.pdf", 最小文件大小: 1024, 文件扩展名: ".pdf"

# 清理下载文件
[清理下载文件], 下载目录: "/downloads", 文件模式: "*.tmp", 保留天数: 7
```

### 认证状态管理

```python
# 保存认证状态
[保存认证状态], 状态名称: "admin_login", 用户名: "admin", 描述: "管理员登录状态"

# 加载认证状态
[加载认证状态], 状态名称: "admin_login", 创建新上下文: True, 验证登录: True

# 列出认证状态
[列出认证状态], 变量名: "auth_states"

# 检查认证状态
[检查认证状态], 状态名称: "admin_login"

# 删除认证状态
[删除认证状态], 状态名称: "admin_login"

# 清除所有认证状态
[清除所有认证状态], 确认清除: True
```

### 验证码识别

```python
# 识别文字验证码（从元素）
[识别文字验证码], 图片源: "#captcha-image", 源类型: "element", 变量名: "captcha_text", 预处理: True

# 识别文字验证码（从文件）
[识别文字验证码], 图片源: "/path/to/captcha.png", 源类型: "file", 变量名: "captcha_text"

# 识别文字验证码（从base64）
[识别文字验证码], 图片源: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", 源类型: "base64", 变量名: "captcha_text"

# 识别文字验证码（从变量）
[识别文字验证码], 图片源: "captcha_image_data", 源类型: "variable", 变量名: "captcha_text"
```

### 浏览器HTTP请求

```python
# 配置浏览器HTTP客户端
[设置浏览器HTTP客户端], 客户端名称: "api", 基础URL: "https://api.example.com", 默认头: '{"Accept": "application/json"}'

# 发送浏览器HTTP请求（利用浏览器cookie和认证状态）
[浏览器HTTP请求], 客户端: "api", 配置: """
request:
  url: "/users"
  method: "GET"
capture:
  user_list: "$.data"
assert:
  - jsonpath: "$.status"
    operator: "=="
    value: "success"
""", 保存响应: "api_response"
```

## 检查功能

```python
# 检查元素是否存在
[检查元素是否存在], 定位器: "#optional-element", 超时时间: 5

# 检查元素是否可见
[检查元素是否可见], 定位器: "#dynamic-element", 超时时间: 5

# 检查元素是否启用
[检查元素是否启用], 定位器: "#submit-button", 超时时间: 5

# 检查元素是否选中
[检查元素是否选中], 定位器: "input[type='checkbox']"

# 检查文本是否包含
[检查文本是否包含], 定位器: ".status", 期望文本: "成功", 超时时间: 5

# 检查元素属性值
[检查元素属性值], 定位器: "input", 属性名: "disabled", 期望值: "true", 超时时间: 5

# 检查页面标题是否包含
[检查页面标题是否包含], 期望标题片段: "首页", 超时时间: 5

# 检查页面URL是否包含
[检查页面URL是否包含], 期望URL片段: "/dashboard", 超时时间: 5

# 多条件检查
[多条件检查], 检查条件列表: [
    {"type": "element_visible", "selector": "#login-button"},
    {"type": "text_contains", "selector": "#message", "expected_text": "欢迎"}
], 逻辑关系: "AND"

# 断言网络响应内容
[断言响应内容], 响应数据: "api_response", 断言类型: "status_code", 期望值: 200
[断言响应内容], 响应数据: "api_response", 断言类型: "json_path", JSON路径: "$.data.length", 期望值: 10
[断言响应内容], 响应数据: "api_response", 断言类型: "text_contains", 期望值: "success"
```

## 其他操作

```python
# 等待指定时间
[等待], 秒数: 3

# 聚焦元素
[聚焦元素], 定位器: "#input-field"

# 滚动元素到视野
[滚动元素到视野], 定位器: "#bottom-element"

# 拖拽元素
[拖拽元素], 源定位器: "#drag-source", 目标定位器: "#drop-target"

# 按键操作
[按键操作], 定位器: "#input-field", 按键: "Enter"

# 逐字符输入（适用于特殊键盘处理）
[逐字符输入], 定位器: "#special-input", 文本: "test", 延迟: 100

# 获取元素文本
[获取元素文本], 定位器: ".result", 变量名: "result_text"

# 获取元素属性
[获取元素属性], 定位器: "img", 属性: "src", 变量名: "image_url", 默认值: ""

# 等待URL变化
[等待URL变化], URL模式: ".*dashboard.*", 超时时间: 10, 变量名: "new_url"

# 设置等待超时
[设置等待超时], 超时时间: 30

# 强制点击元素（忽略状态检查）
[点击元素], 定位器: "#hidden-button", 强制点击: True

# 点击指定索引的元素
[点击元素], 定位器: ".item", 索引: 2

# 只点击可见元素
[点击元素], 定位器: ".dynamic-button", 可见性: True
```

## 配置选项

你可以通过配置文件自定义浏览器行为：

```yaml
# pytest-dsl.yaml
ui:
  default_browser: "chromium"
  headless: False
  viewport_width: 1920
  viewport_height: 1080
  slow_mo: 0
  ignore_https_errors: True
  
  # 浏览器启动配置
  browser_config:
    args:
      - "--disable-web-security"
      - "--allow-running-insecure-content"
```

## 元素获取和操作

### 获取元素信息

```python
# 获取元素文本内容
[获取元素文本], 定位器: ".username", 变量名: "current_user"

# 获取元素属性值
[获取元素属性], 定位器: "img.avatar", 属性: "src", 变量名: "avatar_url"
[获取元素属性], 定位器: "input[name='email']", 属性: "value", 变量名: "email_value", 默认值: "未设置"

# 检查元素是否选中（复选框/单选框）
[检查元素是否选中], 定位器: "input[name='remember_me']"
```

### 元素状态等待

```python
# 等待元素出现并设置超时处理
[等待元素出现], 定位器: "#loading-spinner", 状态: "visible", 超时时间: 5, 失败时抛异常: False

# 等待元素消失
[等待元素出现], 定位器: "#loading-spinner", 状态: "hidden", 超时时间: 10, 失败时抛异常: True

# 等待元素从DOM中移除
[等待元素出现], 定位器: ".temporary-notice", 状态: "detached", 超时时间: 8

# 等待文本出现在页面中
[等待文本出现], 文本: "操作成功", 超时时间: 15, 失败时抛异常: False
```

## 实际应用示例

### 登录测试

```python
@name: "用户登录测试"
@description: "测试用户登录功能"

# 启动浏览器并打开登录页面
[启动浏览器], 浏览器: "chromium"
[打开页面], 地址: "https://example.com/login"

# 等待页面加载
[等待元素出现], 定位器: "#login-form", 状态: "visible"

# 输入用户名和密码
[输入文本], 定位器: "input[name='username']", 文本: "testuser"
[输入文本], 定位器: "input[name='password']", 文本: "password123"

# 点击登录按钮
[点击元素], 定位器: "#login-button"

# 等待登录成功
[等待元素出现], 定位器: ".welcome-message", 状态: "visible", 超时时间: 10

# 验证登录成功
[断言文本内容], 定位器: ".welcome-message", 期望文本: "欢迎", 匹配方式: "contains"
[断言页面URL], 期望URL: "/dashboard", 匹配方式: "contains"

# 清理：关闭浏览器
teardown do
    [关闭浏览器]
end
```

### 表单填写测试

```python
@name: "联系表单测试"
@data: "contact_forms.csv" using csv

[启动浏览器]
[打开页面], 地址: "https://example.com/contact"

# 填写表单
[输入文本], 定位器: "input[name='name']", 文本: "${name}"
[输入文本], 定位器: "input[name='email']", 文本: "${email}"
[选择选项], 定位器: "select[name='subject']", 标签: "${subject}"
[输入文本], 定位器: "textarea[name='message']", 文本: "${message}"

# 上传文件（如果需要）
if "${attachment}" != "" do
    [上传文件], 定位器: "input[type='file']", 文件路径: "${attachment}"
end

# 勾选同意条款
[勾选复选框], 定位器: "input[name='agree_terms']"

# 提交表单
[点击元素], 定位器: "#submit-button"

# 验证提交成功
[等待元素出现], 定位器: ".success-message", 状态: "visible", 超时时间: 15
[断言文本内容], 定位器: ".success-message", 期望文本: "感谢您的留言", 匹配方式: "contains"

teardown do
    [关闭浏览器]
end
```

## 最佳实践

### 1. 使用显式等待

```python
# 好的做法：使用显式等待
[等待元素出现], 定位器: "#dynamic-content", 状态: "visible", 超时时间: 10
[点击元素], 定位器: "#dynamic-content button"

# 避免：使用固定延时
# [等待], 秒数: 5  # 不推荐
```

### 2. 优化定位器

```python
# 好的做法：使用稳定的定位器
[点击元素], 定位器: "[data-testid='submit-button']"
[点击元素], 定位器: "#unique-submit-button"

# 避免：使用脆弱的定位器
# [点击元素], 定位器: "body > div:nth-child(3) > button"  # 不推荐
```

### 3. 适当的错误处理

```python
# 使用检查功能处理可选元素
if [检查元素是否存在], 定位器: ".close-popup", 超时时间: 2 do
    [点击元素], 定位器: ".close-popup"
end

# 继续主要测试流程
[输入文本], 定位器: "#search-input", 文本: "pytest-dsl"
```

### 4. 资源清理

```python
# 在teardown中确保清理资源
teardown do
    [截图], 文件名: "final_state.png"
    [关闭浏览器]
end
```

### 5. 使用认证状态管理

```python

# 检查是否已有登录状态
if ![检查认证状态], 状态名称: "admin_user" do
    [启动浏览器]
    [打开页面], 地址: "https://example.com/login"
    [输入文本], 定位器: "input[name='username']", 文本: "admin"
    [输入文本], 定位器: "input[name='password']", 文本: "password"
    [点击元素], 定位器: "#login-button"
    [等待元素出现], 定位器: ".dashboard", 状态: "visible"
    [保存认证状态], 状态名称: "admin_user", 用户名: "admin", 描述: "管理员用户"
    [关闭浏览器]
end

# 在测试中加载认证状态
[加载认证状态], 状态名称: "admin_user", 创建新上下文: True
[打开页面], 地址: "https://example.com/dashboard"
# 现在已经是登录状态，可以直接测试功能
```

## 关键字参考

### 浏览器管理类
- `[启动浏览器]` - 启动指定类型的浏览器
- `[关闭浏览器]` - 关闭浏览器实例
- `[设置等待超时]` - 设置默认等待超时时间

### 导航类
- `[打开页面]` - 导航到指定URL
- `[刷新页面]` - 刷新当前页面
- `[后退]` - 浏览器后退
- `[前进]` - 浏览器前进
- `[获取当前地址]` - 获取当前页面URL
- `[获取页面标题]` - 获取页面标题

### 元素交互类
- `[点击元素]` - 点击页面元素
- `[双击元素]` - 双击页面元素
- `[右键点击元素]` - 右键点击页面元素
- `[悬停元素]` - 鼠标悬停在元素上
- `[输入文本]` - 在输入框中输入文本
- `[清空文本]` - 清空输入框内容
- `[逐字符输入]` - 逐个字符输入文本
- `[按键操作]` - 模拟键盘按键
- `[聚焦元素]` - 聚焦到指定元素
- `[滚动元素到视野]` - 滚动使元素可见
- `[拖拽元素]` - 拖拽元素到目标位置

### 表单操作类
- `[勾选复选框]` - 勾选复选框
- `[取消勾选复选框]` - 取消勾选复选框
- `[设置复选框状态]` - 设置复选框状态
- `[选择单选框]` - 选择单选框
- `[选择下拉选项]` - 选择下拉框选项
- `[选择选项]` - 通用选项选择
- `[上传文件]` - 上传文件

### 等待类
- `[等待元素出现]` - 等待元素达到指定状态
- `[等待文本出现]` - 等待文本在页面中出现
- `[等待新页面]` - 等待新页面打开
- `[等待网络请求]` - 等待特定网络请求
- `[等待网络响应]` - 等待特定网络响应
- `[等待下载]` - 等待文件下载完成
- `[等待URL变化]` - 等待页面URL变化

### 断言类
- `[断言元素存在]` - 断言元素存在于DOM中
- `[断言元素可见]` - 断言元素可见
- `[断言元素隐藏]` - 断言元素隐藏
- `[断言元素启用]` - 断言元素启用状态
- `[断言元素禁用]` - 断言元素禁用状态
- `[断言文本内容]` - 断言元素文本内容
- `[断言属性值]` - 断言元素属性值
- `[断言输入值]` - 断言输入框的值
- `[断言复选框状态]` - 断言复选框选中状态
- `[断言元素数量]` - 断言匹配元素的数量
- `[断言页面标题]` - 断言页面标题
- `[断言页面URL]` - 断言页面URL
- `[断言响应内容]` - 断言网络响应内容

### 检查类
- `[检查元素是否存在]` - 检查元素是否存在
- `[检查元素是否可见]` - 检查元素是否可见
- `[检查元素是否启用]` - 检查元素是否启用
- `[检查元素是否选中]` - 检查元素是否选中
- `[检查文本是否包含]` - 检查文本是否包含指定内容
- `[检查元素属性值]` - 检查元素属性值
- `[检查页面标题是否包含]` - 检查页面标题是否包含文本
- `[检查页面URL是否包含]` - 检查页面URL是否包含文本
- `[多条件检查]` - 执行多个条件检查

### 获取类
- `[获取元素文本]` - 获取元素文本内容
- `[获取元素属性]` - 获取元素属性值
- `[获取页面列表]` - 获取所有页面列表
- `[获取视口大小]` - 获取浏览器视口大小

### 页面管理类
- `[新建页面]` - 创建新的浏览器页面
- `[切换页面]` - 切换到指定页面
- `[切换到最新页面]` - 切换到最新创建的页面
- `[根据URL查找页面]` - 根据URL查找页面
- `[根据标题查找页面]` - 根据标题查找页面

### 捕获类
- `[截图]` - 截取页面或元素截图
- `[开始录制]` - 开始录制视频
- `[停止录制]` - 停止录制视频
- `[执行JavaScript]` - 执行JavaScript代码
- `[设置视口大小]` - 设置浏览器视口大小

### 下载管理类
- `[监听下载]` - 监听页面下载事件
- `[验证下载文件]` - 验证下载的文件
- `[清理下载文件]` - 清理下载文件

### 认证管理类
- `[保存认证状态]` - 保存当前认证状态
- `[加载认证状态]` - 加载保存的认证状态
- `[列出认证状态]` - 列出所有认证状态
- `[检查认证状态]` - 检查认证状态是否存在
- `[删除认证状态]` - 删除指定认证状态
- `[清除认证状态]` - 清除指定认证状态
- `[清除所有认证状态]` - 清除所有认证状态

### 验证码处理类
- `[识别文字验证码]` - 识别图片中的文字验证码

### HTTP请求类
- `[设置浏览器HTTP客户端]` - 配置浏览器HTTP客户端
- `[浏览器HTTP请求]` - 发送基于浏览器的HTTP请求

通过这些UI测试关键字，你可以轻松创建强大的Web应用自动化测试，无需深入了解Playwright等底层工具的复杂API。 