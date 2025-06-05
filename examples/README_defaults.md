# pytest-dsl 关键字默认值功能详解

## 📋 概述

pytest-dsl现在支持为关键字参数设置默认值，这个功能让DSL编写更加简洁高效。使用默认值，您只需传递必要的参数，其他参数会自动使用预设的合理默认值。

## 🔧 核心改进

### 修复None默认值问题

之前的版本中，某些关键字使用`None`作为默认值，这在DSL语法中无法被识别。现在我们已经全面修复这个问题：

**修复前的问题：**
```python
# ❌ 问题：DSL无法识别None默认值
{'name': '时区', 'mapping': 'timezone', 'description': '时区', 'default': None}
```

**修复后的改进：**
```python
# ✅ 改进：使用具体实用的默认值
{'name': '时区', 'mapping': 'timezone', 'description': '时区', 'default': 'Asia/Shanghai'}
```

### 主要修复项目

| 关键字 | 参数 | 修复前 | 修复后 | 说明 |
|--------|------|--------|--------|------|
| 获取当前时间 | 格式 | `None` | `'timestamp'` | 默认返回时间戳 |
| 获取当前时间 | 时区 | `None` | `'Asia/Shanghai'` | 默认使用北京时区 |
| 等待 | 秒数 | 无默认值 | `1` | 默认等待1秒 |
| 字符串操作 | 操作 | 无默认值 | `'strip'` | 默认去空格操作 |
| 字符串操作 | 参数1 | 无默认值 | `''` | 默认空字符串 |
| 字符串操作 | 参数2 | 无默认值 | `''` | 默认空字符串 |

## 🎯 内置关键字默认值

### 时间相关关键字

#### 获取当前时间（修复后）
```python
# 使用默认值 - 返回北京时区的时间戳
timestamp = [获取当前时间]

# 使用默认时区，指定格式
beijing_time = [获取当前时间], 格式: "%Y-%m-%d %H:%M:%S"

# 使用本地时区
local_time = [获取当前时间], 格式: "%Y-%m-%d %H:%M:%S", 时区: "local"
```

**默认值说明：**
- `格式`: `'timestamp'` - 返回整数时间戳，不再是字符串
- `时区`: `'Asia/Shanghai'` - 使用北京时区，更符合国内使用习惯

#### 等待（修复后）
```python
# 使用默认值 - 等待1秒
[等待]

# 自定义等待时间
[等待], 秒数: 2.5
```

**默认值说明：**
- `秒数`: `1` - 默认等待1秒，常用的等待时间

### 字符串相关关键字

#### 字符串操作（新增默认值）
```python
# 使用默认操作 - 去空格
cleaned = [字符串操作], 字符串: "  hello world  "

# 使用默认分隔符分割 - 按空格分割
words = [字符串操作], 操作: "split", 字符串: "apple orange banana"

# 指定分隔符
items = [字符串操作], 操作: "split", 字符串: "a,b,c", 参数1: ","
```

**默认值说明：**
- `操作`: `'strip'` - 最常用的去空格操作
- `参数1`: `''` - 空字符串，避免传递`None`
- `参数2`: `''` - 空字符串，避免传递`None`

### 数据生成关键字

#### 生成随机数（已有默认值）
```python
# 使用默认值 - 0到100的整数
random_int = [生成随机数]

# 部分自定义
random_small = [生成随机数], 最大值: 10
```

**默认值说明：**
- `最小值`: `0` - 常用的起始值
- `最大值`: `100` - 合理的范围上限
- `小数位数`: `0` - 默认生成整数

#### 生成随机字符串（已有默认值）
```python
# 使用默认值 - 8位字母数字混合
random_str = [生成随机字符串]

# 自定义长度
long_str = [生成随机字符串], 长度: 16
```

**默认值说明：**
- `长度`: `8` - 适中的字符串长度
- `类型`: `'alphanumeric'` - 字母数字混合，最通用

## 🛠️ 自定义关键字默认值

### 定义带默认值的关键字

```python
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('HTTP请求增强', [
    {'name': '地址', 'mapping': 'url', 'description': '请求地址'},
    {'name': '方法', 'mapping': 'method', 'description': 'HTTP方法', 'default': 'GET'},
    {'name': '超时', 'mapping': 'timeout', 'description': '超时时间（秒）', 'default': 30},
    {'name': '重试次数', 'mapping': 'retries', 'description': '重试次数', 'default': 3},
    {'name': '验证SSL', 'mapping': 'verify_ssl', 'description': '是否验证SSL证书', 'default': True},
    {'name': '用户代理', 'mapping': 'user_agent', 'description': 'User-Agent头', 'default': 'pytest-dsl/1.0'}
])
def enhanced_http_request(**kwargs):
    """增强的HTTP请求关键字，带实用默认值"""
    url = kwargs.get('url')
    method = kwargs.get('method', 'GET')
    timeout = kwargs.get('timeout', 30)
    retries = kwargs.get('retries', 3)
    verify_ssl = kwargs.get('verify_ssl', True)
    user_agent = kwargs.get('user_agent', 'pytest-dsl/1.0')
    
    # 实现HTTP请求逻辑...
    return {
        'status': 'success',
        'method': method,
        'url': url,
        'config': {
            'timeout': timeout,
            'retries': retries,
            'verify_ssl': verify_ssl,
            'user_agent': user_agent
        }
    }
```

### 在DSL中使用
```python
# 最简单的调用 - 只传递必需参数
response1 = [HTTP请求增强], 地址: "https://api.example.com/users"

# 部分自定义 - 只覆盖需要的参数
response2 = [HTTP请求增强], 地址: "https://api.example.com/posts", 方法: "POST", 超时: 60

# 完全自定义
response3 = [HTTP请求增强], 地址: "https://internal.api.com", 方法: "PUT", 超时: 120, 重试次数: 5, 验证SSL: False
```

## 🌐 远程关键字默认值

远程关键字完全支持默认值功能，默认值会在客户端和服务器之间正确传递：

```python
# 远程服务器上定义的关键字会保持完整的默认值支持
remote_result = server1|[HTTP请求增强], 地址: "https://remote.api.com"
# 默认值自动应用：方法=GET, 超时=30, 重试=3, SSL验证=True
```

## ✨ 最佳实践

### 1. 默认值设计原则

- **实用性优先**：选择最常用的值作为默认值
- **避免None**：使用具体值而不是`None`
- **类型一致**：确保默认值与参数类型匹配
- **文档清晰**：在描述中说明默认值的含义

### 2. 推荐的默认值模式

```python
# ✅ 好的默认值设计
{'name': '端口', 'mapping': 'port', 'description': '服务端口', 'default': 8080}
{'name': '协议', 'mapping': 'protocol', 'description': '通信协议', 'default': 'http'}
{'name': '超时', 'mapping': 'timeout', 'description': '超时时间（秒）', 'default': 30}
{'name': '重试', 'mapping': 'retries', 'description': '重试次数', 'default': 3}
{'name': '编码', 'mapping': 'encoding', 'description': '字符编码', 'default': 'utf-8'}

# ❌ 避免的默认值设计
{'name': '端口', 'mapping': 'port', 'description': '服务端口', 'default': None}
{'name': '配置', 'mapping': 'config', 'description': '配置信息', 'default': {}}  # 可变对象
```

### 3. DSL编写技巧

```python
# 利用默认值简化DSL
@name: "高效API测试"

# 基础请求 - 利用所有默认值
basic_response = [HTTP请求增强], 地址: "https://api.example.com/health"

# 批量测试 - 只改变必要参数
for endpoint in ["users", "posts", "comments"] do
    response = [HTTP请求增强], 地址: "https://api.example.com/${endpoint}"
    [断言], 条件: "${response['status']} == 200", 消息: "${endpoint} 接口正常"
end

# 错误处理测试 - 调整重试和超时
error_response = [HTTP请求增强], 地址: "https://api.example.com/error", 重试次数: 1, 超时: 5
```

## 🔧 技术实现细节

### 默认值应用流程

1. **注册时收集**：关键字注册时收集所有默认值
2. **执行时应用**：先设置默认值，再用传入参数覆盖
3. **远程传递**：默认值信息在远程调用时完整传递
4. **文档生成**：自动在文档中显示默认值信息

### 内部数据结构

```python
# 关键字信息结构
{
    'func': function_object,
    'mapping': {'中文名': 'english_name'},
    'parameters': [Parameter对象列表],
    'defaults': {'english_name': default_value},  # 默认值字典
    'remote': False
}
```

## 🚀 升级指南

如果您已经在使用pytest-dsl，升级到支持修复的默认值版本：

### 兼容性说明

- ✅ **完全向后兼容**：现有DSL无需修改
- ✅ **增强功能**：现有关键字获得更好的默认值
- ✅ **渐进采用**：可以逐步利用默认值简化DSL

### 升级步骤

1. **更新代码**：拉取最新版本
2. **验证测试**：运行现有测试确保兼容性
3. **优化DSL**：逐步移除不必要的参数传递
4. **享受提升**：体验更简洁的DSL编写

## 📊 效果对比

### 修复前后对比

**修复前：**
```python
# 时间获取需要处理None值
time_result = [获取当前时间], 格式: "%Y-%m-%d %H:%M:%S", 时区: "Asia/Shanghai"

# 等待必须传递参数
[等待], 秒数: 1

# 字符串操作容易出错
cleaned = [字符串操作], 操作: "strip", 字符串: "  text  ", 参数1: "", 参数2: ""
```

**修复后：**
```python
# 时间获取更简洁
formatted_time = [获取当前时间], 格式: "%Y-%m-%d %H:%M:%S"  # 自动使用北京时区
timestamp = [获取当前时间]  # 自动返回时间戳

# 等待更直观
[等待]  # 自动等待1秒

# 字符串操作更简单
cleaned = [字符串操作], 字符串: "  text  "  # 自动使用strip操作
```

### DSL简化效果

**简化前：** 需要传递7个参数
```python
response = [HTTP请求], 地址: "https://api.com", 方法: "GET", 超时: 30, 重试次数: 3, 验证SSL: True, 用户代理: "test", 编码: "utf-8"
```

**简化后：** 只需传递1个必需参数
```python
response = [HTTP请求], 地址: "https://api.com"  # 其他6个参数自动使用默认值
```

**代码减少：** ~85%的参数传递代码被默认值取代！

---

## 🎉 总结

通过修复None默认值问题和优化默认值设计，pytest-dsl现在提供了：

- **🎯 更实用的默认值**：如北京时区、合理的超时时间等
- **🚀 更简洁的DSL**：大幅减少必需的参数传递
- **🛡️ 更健壮的设计**：避免了DSL无法识别None的问题
- **📖 更清晰的文档**：默认值信息自动显示在文档中
- **🌐 完整的远程支持**：远程关键字保持一致的默认值体验

现在开始使用修复后的默认值功能，让您的测试自动化更加高效！ 