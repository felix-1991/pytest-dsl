# HTTP请求断言重试功能

HTTP请求断言重试功能允许您在断言失败时自动重试请求，这对于测试异步API或需要等待状态变化的场景非常有用。最新的实现支持在配置中直接定义重试策略，并且可以针对特定断言进行重试控制。

## 基本概念

断言重试功能主要解决以下场景：

1. **异步处理**：当API需要在后台处理请求，返回结果需要时间
2. **状态转换**：需要等待资源状态从一个状态转变为另一个状态
3. **数据准备**：需要等待数据被生成或更新
4. **负载平衡**：在高负载下，某些请求可能临时失败需要重试

## 重试配置方式

断言重试支持以下几种配置方式，按优先级从高到低排序：

### 1. 独立的retry_assertions配置（推荐）

新增的独立配置块，与asserts同级，可以更集中和清晰地定义重试策略：

```yaml
method: GET
url: https://api.example.com/tasks/123
asserts:
  - ["status", "eq", 200]
  - ["jsonpath", "$.status", "eq", "completed"]
retry_assertions:
  count: 3                # 全局重试次数
  interval: 1             # 全局重试间隔（秒）
  all: true               # 是否重试所有断言
  indices: [1]            # 指定要重试的断言索引（从0开始计数）
  specific:               # 针对特定断言的重试配置
    "1": {                # 断言索引为1的特定配置
      count: 5,           # 特定重试次数
      interval: 2         # 特定重试间隔
    }
```

### 2. 断言级别详细配置

为特定断言指定详细的重试配置：

```yaml
asserts:
  - ["jsonpath", "$.status", "eq", "completed", {"retry": {"count": 5, "interval": 2}}]
```

### 3. 断言级别简化配置

使用简化语法启用断言重试（使用全局默认配置）：

```yaml
asserts:
  - ["jsonpath", "$.status", "eq", "completed", {"retry": true}]
```

### 4. 全局重试配置（传统方式）

在请求配置中设置全局重试策略：

```yaml
retry:
  count: 3
  interval: 1
asserts:
  - ["status", "eq", 200]
  - ["jsonpath", "$.data", "exists"]
```

### 5. 关键字参数

通过关键字参数设置重试（向后兼容旧版本）：

```
[HTTP请求],客户端:'default',配置:'...',断言重试次数:3,断言重试间隔:1
```

## 独立重试配置详解

推荐使用新的`retry_assertions`配置块，它提供了更强大和灵活的断言重试控制：

```yaml
retry_assertions:
  # 全局设置
  count: 3                # 重试次数，默认为3次
  interval: 1.5           # 重试间隔（秒），默认为1秒
  
  # 控制哪些断言会重试
  all: true               # 设置为true时重试所有断言（默认为false）
  indices: [1, 2, 4]      # 指定断言索引列表（从0开始计数）
  
  # 为特定断言指定不同的重试策略
  specific:
    "1": {                # 断言索引为1的配置
      count: 5,           # 特定重试次数
      interval: 2         # 特定重试间隔
    }
    "2": {                # 断言索引为2的配置
      count: 10,
      interval: 0.5
    }
```

### 重试配置优先级

当存在多种重试配置时，按照以下优先级处理：

1. 断言级别的`retry`配置 (最高优先级)
2. `retry_assertions.specific`中针对特定断言的配置
3. `retry_assertions`中的全局设置
4. 传统的`retry`配置
5. 默认值 (最低优先级)

## 配置项说明

### 独立重试配置选项

```yaml
retry_assertions:
  count: 3                # 重试次数，默认为3次
  interval: 1             # 重试间隔（秒），默认为1秒
  all: true               # 是否重试所有断言
  indices: [1, 2]         # 指定要重试的断言索引（基于0的索引）
  specific:               # 针对特定断言的重试配置
    "1": { count: 5, interval: 2 }  # 索引1的断言特定配置
```

### 传统重试配置

```yaml
retry:
  count: 3       # 重试次数，默认为3次
  interval: 1    # 重试间隔（秒），默认为1秒
```


## 重试行为说明

1. **选择性重试**：只有标记为可重试的断言失败时才会重试
2. **重试策略**：每次重试前会等待设定的间隔时间
3. **最大重试次数**：达到最大重试次数后，如果断言仍然失败，将抛出异常
4. **优先级**：断言级别配置优先于全局配置
5. **不同断言不同配置**：可以为不同断言设置不同的重试策略

## 示例

### 示例1：使用独立重试配置（推荐）

```yaml
method: GET
url: https://api.example.com/tasks/123
asserts:
  - ["status", "eq", 200]
  - ["jsonpath", "$.status", "eq", "completed"]
  - ["jsonpath", "$.result", "exists"]
retry_assertions:
  count: 5
  interval: 2
  all: true
```

### 示例2：只对特定断言索引进行重试

```yaml
method: GET
url: https://api.example.com/tasks/123
asserts:
  - ["status", "eq", 200]  # 索引0，不重试
  - ["jsonpath", "$.status", "eq", "completed"]  # 索引1，将重试
  - ["jsonpath", "$.result", "exists"]  # 索引2，将重试
retry_assertions:
  count: 3
  interval: 1
  indices: [1, 2]  # 只重试索引1和2的断言
```

### 示例3：为特定断言指定不同的重试策略

```yaml
method: GET
url: https://api.example.com/tasks/123
asserts:
  - ["status", "eq", 200]  # 索引0
  - ["jsonpath", "$.status", "eq", "completed"]  # 索引1
  - ["jsonpath", "$.result", "exists"]  # 索引2
retry_assertions:
  count: 3  # 全局重试设置
  interval: 1
  indices: [1, 2]  # 只重试索引1和2
  specific:
    "1": {  # 索引1使用特定配置
      count: 10,
      interval: 3
    }
```


## 最佳实践

1. **使用独立的retry_assertions配置**：更清晰地定义重试策略
2. **适用场景识别**：只对可能需要等待的断言启用重试，比如状态检查
3. **合理的重试间隔**：设置与业务流程匹配的重试间隔
4. **最大重试次数控制**：避免过长的等待时间
5. **断言分类**：将致命错误和临时状态区分对待
   - 致命错误（如404状态码）不应该重试
   - 临时状态（如"pending"状态）适合重试

## 注意事项

1. 每次重试都会重新发送完整的HTTP请求
2. 断言重试会增加测试执行时间
3. 对于幂等API（GET、HEAD等）比非幂等API（POST、PUT等）更适合使用重试
4. 当使用非幂等API时，需要考虑重试的副作用 