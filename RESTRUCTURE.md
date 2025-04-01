# pytest-dsl 项目结构调整

本文档描述了 pytest-dsl 项目的结构调整过程，包括目录结构优化和引入 uv 包管理工具。

## 目录结构变更

项目结构已从原来的平铺结构调整为符合 Python 包标准的嵌套结构：

**之前的结构**:
```
pytest-dsl/
├── core/               # 核心模块
├── keywords/           # 关键字定义模块
├── examples/           # 示例代码
├── docs/               # 文档
├── conftest.py         # pytest 插件配置
├── main.py             # 主入口
└── requirements.txt    # 依赖配置
```

**调整后的结构**:
```
pytest-dsl/
├── pytest_dsl/         # 主包目录
│   ├── core/           # 核心模块
│   ├── keywords/       # 关键字定义模块
│   ├── examples/       # 示例代码
│   ├── docs/           # 文档
│   ├── __init__.py     # 包初始化文件
│   ├── plugin.py       # pytest 插件入口(原 conftest.py)
│   └── cli.py          # 命令行工具入口(原 main.py)
├── tests/              # 测试目录
│   ├── test_core/      # 核心模块测试
│   └── test_keywords/  # 关键字模块测试
├── pyproject.toml      # 项目元数据和构建配置
├── setup.py            # 兼容旧版安装工具
├── MANIFEST.in         # 包含非Python文件的配置
├── LICENSE             # 许可证文件
└── README.md           # 项目说明文档
```

## 引入 uv 包管理

[uv](https://github.com/astral-sh/uv) 是一个新的 Python 包管理工具，提供了比 pip 更快的性能和更好的依赖解析能力。本项目现已支持使用 uv 进行依赖管理。

uv 相关配置文件:
- `.uv/settings.toml` - uv 配置文件，包含开发依赖和虚拟环境设置

## 迁移流程

项目提供了两个脚本来帮助完成迁移:

1. `migrate_code.py` - 将原有代码移动到新的目录结构，并更新导入语句
2. `setup_env.sh` - 设置开发环境，安装 uv 并创建虚拟环境

### 如何执行迁移

1. 运行迁移脚本，将现有代码移入新结构中:
   ```bash
   python migrate_code.py
   ```

2. 使用 uv 创建开发环境:
   ```bash
   bash setup_env.sh
   ```

### 迁移后的文件变化

迁移过程中主要做了以下变更:

1. 将 `conftest.py` 中的内容移到 `pytest_dsl/plugin.py`
2. 将 `main.py` 中的内容移到 `pytest_dsl/cli.py`
3. 将 `core/`, `keywords/` 等目录移动到 `pytest_dsl/` 下
4. 更新了所有模块中的导入语句，使用 `pytest_dsl.` 前缀

## 安装与使用

### 开发模式安装

使用 uv 安装:
```bash
uv pip install -e .
```

或使用传统 pip 安装:
```bash
pip install -e .
```

### 运行测试

```bash
pytest tests/
```

### 使用命令行工具

```bash
pytest-dsl your_test_file.auto
```

## 附加说明

- `MANIFEST.in` 确保非 Python 文件也会被包含在安装包中
- `.gitignore` 已更新，包含更多适用于 Python 项目的忽略规则
- 所有原有功能保持不变，仅调整了项目结构 