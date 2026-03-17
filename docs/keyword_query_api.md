# pytest-dsl 关键字查询 API

pytest-dsl 提供了统一的关键字查询和信息获取 API，方便其他程序查询和使用关键字信息。

## 概述

通过 `pytest_dsl` 包，您可以：

- 📋 **列出所有关键字** - 获取完整的关键字列表和详细信息
- 🔍 **搜索关键字** - 根据名称模式搜索匹配的关键字
- 📖 **查看单个关键字** - 获取特定关键字的详细信息
- 📊 **按类别筛选** - 按关键字类别（内置、插件、自定义等）筛选
- 📤 **多格式导出** - 支持 JSON、文本、HTML 格式输出

## 核心功能

### 1. 列出关键字

#### `list_keywords()` 函数

```python
import pytest_dsl

# 获取所有关键字（JSON格式）
keywords_data = pytest_dsl.list_keywords(
    output_format='json',
    print_summary=False  # 不打印摘要
)

# 按类别筛选
builtin_keywords = pytest_dsl.list_keywords(
    output_format='json',
    category_filter='builtin',
    print_summary=False
)

# 搜索特定名称
http_keywords = pytest_dsl.list_keywords(
    output_format='json',
    name_filter='HTTP',
    print_summary=False
)

# 输出到文件
pytest_dsl.list_keywords(
    output_format='html',
    output_file='keywords.html'
)
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| `output_format` | str | 'json' | 输出格式：'json', 'text', 'html' |
| `name_filter` | str | None | 名称过滤器（支持部分匹配） |
| `category_filter` | str | 'all' | 类别过滤器：'builtin', 'plugin', 'custom', 'project_custom', 'remote', 'all' |
| `include_remote` | bool | False | 是否包含远程关键字 |
| `output_file` | str | None | 输出文件路径 |
| `print_summary` | bool | True | 是否打印摘要信息 |

#### 返回值格式 (JSON)

```json
{
  "summary": {
    "total_count": 35,
    "category_counts": {
      "builtin": 29,
      "project_custom": 6
    },
    "source_counts": {
      "builtin:pytest-dsl内置": 29,
      "project_custom:/path/to/custom.resource": 6
    }
  },
  "keywords": [
    {
      "name": "HTTP请求",
      "category": "builtin",
      "source_info": {
        "type": "builtin",
        "name": "pytest-dsl内置",
        "display_name": "pytest-dsl内置",
        "module": "pytest_dsl.keywords.http_keywords",
        "plugin_module": ""
      },
      "parameters": [
        {
          "name": "客户端",
          "mapping": "client",
          "description": "HTTP客户端名称",
          "default": "default"
        },
        {
          "name": "配置",
          "mapping": "config",
          "description": "请求配置"
        }
      ],
      "returns": {
        "type": "dict",
        "description": "包含 result、side_effects、metadata 的 HTTP 执行结果"
      },
      "documentation": "发送HTTP请求并返回响应"
    }
  ]
}
```

### 2. 搜索关键字

#### `search_keywords()` 函数

```python
import pytest_dsl

# 搜索包含特定模式的关键字
http_keywords = pytest_dsl.search_keywords('HTTP')
assert_keywords = pytest_dsl.search_keywords('断言')

# 处理搜索结果
for keyword_info in http_keywords:
    print(f"关键字: {keyword_info.name}")
    print(f"类别: {keyword_info.category}")
    print(f"参数数量: {len(keyword_info.parameters)}")
    print(f"说明: {keyword_info.documentation}")
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| `pattern` | str | - | 搜索模式（支持部分匹配） |
| `include_remote` | bool | False | 是否包含远程关键字 |

#### 返回值

返回 `List[KeywordInfo]`，每个 `KeywordInfo` 对象包含以下属性：

- `name`: 关键字名称
- `category`: 关键字类别
- `source_info`: 来源信息
- `parameters`: 参数列表
- `returns`: 结构化返回值信息，包含 `type` 和可选的 `description`
- `documentation`: 文档字符串
- `file_location`: 文件位置（仅项目自定义关键字）
- `remote_info`: 远程信息（仅远程关键字）

### 3. 获取单个关键字信息

#### `get_keyword_info()` 函数

```python
import pytest_dsl

# 获取特定关键字的详细信息
keyword_info = pytest_dsl.get_keyword_info('HTTP请求')

if keyword_info:
    print(f"关键字: {keyword_info.name}")
    print(f"类别: {keyword_info.category}")
    print(f"来源: {keyword_info.source_info['name']}")
    
    # 参数信息
    for param in keyword_info.parameters:
        print(f"参数: {param['name']} - {param['description']}")
        if 'default' in param:
            print(f"  默认值: {param['default']}")

    if keyword_info.returns:
        print(f"返回类型: {keyword_info.returns['type']}")
        print(f"返回说明: {keyword_info.returns.get('description', '')}")
    
    # 文档
    if keyword_info.documentation:
        print(f"说明: {keyword_info.documentation}")
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| `keyword_name` | str | - | 关键字名称 |
| `include_remote` | bool | False | 是否包含远程关键字 |

#### 返回值

返回 `KeywordInfo` 对象或 `None`（如果未找到）。

## 高级用法

### 1. 关键字统计分析

```python
import pytest_dsl

# 获取所有关键字数据
keywords_data = pytest_dsl.list_keywords(
    output_format='json',
    print_summary=False
)

# 统计参数数量分布
param_stats = {}
for keyword in keywords_data['keywords']:
    param_count = len(keyword['parameters'])
    param_stats[param_count] = param_stats.get(param_count, 0) + 1

print("参数数量分布:")
for count, num_keywords in sorted(param_stats.items()):
    print(f"  {count} 个参数: {num_keywords} 个关键字")
```

### 2. 生成文档

```python
import pytest_dsl

def generate_keyword_docs():
    """生成关键字文档"""
    keywords_data = pytest_dsl.list_keywords(
        output_format='json',
        print_summary=False
    )
    
    # 按类别分组
    categories = {}
    for keyword in keywords_data['keywords']:
        category = keyword['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(keyword)
    
    # 生成 Markdown
    markdown = ["# 关键字参考手册\n"]
    
    for category, keywords in categories.items():
        markdown.append(f"\n## {category.title()} 关键字\n")
        
        for keyword in sorted(keywords, key=lambda x: x['name']):
            markdown.append(f"### {keyword['name']}\n")
            
            if keyword.get('documentation'):
                markdown.append(f"{keyword['documentation']}\n")
            
            if keyword['parameters']:
                markdown.append("**参数:**\n")
                for param in keyword['parameters']:
                    line = f"- `{param['name']}`: {param['description']}"
                    if param.get('default') is not None:
                        line += f" (默认: `{param['default']}`)"
                    markdown.append(line + "\n")

            if keyword.get('returns'):
                markdown.append(
                    f"**返回类型:** `{keyword['returns']['type']}`\n"
                )
                if keyword['returns'].get('description'):
                    markdown.append(
                        f"**返回说明:** {keyword['returns']['description']}\n"
                    )
            
            markdown.append("\n")
    
    return ''.join(markdown)

# 生成并保存文档
docs = generate_keyword_docs()
with open('keyword_reference.md', 'w', encoding='utf-8') as f:
    f.write(docs)
```

### 3. 关键字验证

```python
import pytest_dsl

def validate_dsl_keywords(dsl_content):
    """验证DSL中使用的关键字是否存在"""
    # 获取所有可用关键字
    available_keywords = set()
    keywords_data = pytest_dsl.list_keywords(
        output_format='json',
        print_summary=False
    )
    
    for keyword in keywords_data['keywords']:
        available_keywords.add(keyword['name'])
    
    # 解析DSL中使用的关键字（简化示例）
    used_keywords = set()
    for line in dsl_content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            # 假设关键字在行首（实际解析会更复杂）
            if ':' in line:
                keyword = line.split(':')[0].strip()
                used_keywords.add(keyword)
    
    # 检查未定义的关键字
    undefined_keywords = used_keywords - available_keywords
    
    if undefined_keywords:
        print("发现未定义的关键字:")
        for keyword in undefined_keywords:
            print(f"  - {keyword}")
            # 建议相似的关键字
            suggestions = pytest_dsl.search_keywords(keyword[:3])
            if suggestions:
                print(f"    建议: {', '.join([kw.name for kw in suggestions[:3]])}")
    else:
        print("所有关键字都已定义")
```

## KeywordInfo 类

`KeywordInfo` 类提供了关键字的完整信息：

### 属性

- **name** (str): 关键字名称
- **category** (str): 关键字类别 ('builtin', 'plugin', 'custom', 'project_custom', 'remote')
- **source_info** (dict): 来源信息
- **parameters** (list): 参数列表
- **documentation** (str): 文档字符串
- **file_location** (str, optional): 文件位置（项目自定义关键字）
- **remote_info** (dict, optional): 远程关键字信息

### 示例

```python
keyword_info = pytest_dsl.get_keyword_info('HTTP请求')

print(f"名称: {keyword_info.name}")
print(f"类别: {keyword_info.category}")
print(f"来源模块: {keyword_info.source_info['module']}")

# 遍历参数
for param in keyword_info.parameters:
    print(f"参数: {param['name']}")
    print(f"  映射: {param['mapping']}")
    print(f"  描述: {param['description']}")
    if 'default' in param:
        print(f"  默认值: {param['default']}")
```

## 与 CLI 的关系

这些 API 函数与 CLI 工具使用相同的底层实现：

```bash
# CLI 命令
pytest-dsl list-keywords --format json --output keywords.json

# 等价的 Python 代码
pytest_dsl.list_keywords(
    output_format='json',
    output_file='keywords.json'
)
```

这种设计确保了 CLI 和程序化访问的一致性，减少了代码重复。

## 使用场景

### 1. IDE 插件开发

```python
# 为 IDE 提供关键字自动补全
def get_keyword_completions(prefix):
    keywords = pytest_dsl.search_keywords(prefix)
    return [
        {
            'name': kw.name,
            'detail': kw.documentation.split('\n')[0] if kw.documentation else '',
            'parameters': [p['name'] for p in kw.parameters]
        }
        for kw in keywords
    ]
```

### 2. 测试框架集成

```python
# 在测试运行前验证关键字
def pre_test_validation():
    # 检查所有必需的关键字是否可用
    required_keywords = ['HTTP请求', '断言相等', '设置变量']
    
    for keyword_name in required_keywords:
        if not pytest_dsl.get_keyword_info(keyword_name):
            raise ValueError(f"缺少必需的关键字: {keyword_name}")
```

### 3. 文档生成

```python
# 自动生成项目的关键字文档
def update_project_docs():
    # 只导出项目自定义关键字
    project_keywords = pytest_dsl.list_keywords(
        output_format='html',
        category_filter='project_custom',
        output_file='docs/custom_keywords.html'
    )
```

## 注意事项

1. **性能**: 首次调用时会加载所有关键字，后续调用会使用缓存
2. **远程关键字**: 默认不包含远程关键字，需要显式启用
3. **项目上下文**: 函数会自动检测当前项目的自定义关键字
4. **异常处理**: 建议在生产代码中添加适当的异常处理

## 完整示例

查看 `examples/keyword_query_example.py` 文件获取完整的使用示例。 
