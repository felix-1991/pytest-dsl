# pytest-dsl 安装指南

## 前置条件

- Python >= 3.8
- pip 或 uv 包管理器

## 使用 uv 安装（推荐）

[uv](https://github.com/astral-sh/uv) 是一个现代化的 Python 包管理工具，速度更快，依赖解析更可靠。

### 安装 uv

```bash
# 在 Linux/macOS 上安装 uv
curl -sSf https://install.determinate.systems/uv | sh

# 在 Windows 上，建议使用官方安装方法，参见 uv 文档
```

### 使用 uv 安装 pytest-dsl

```bash
# 全局安装
uv pip install pytest-dsl

# 开发模式安装（从本地源码）
uv pip install -e .
```

### 使用 uv 创建虚拟环境

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境（Linux/macOS）
source .venv/bin/activate

# 激活虚拟环境（Windows）
.venv\Scripts\activate
```

## 使用传统 pip 安装

如果你更习惯使用传统的 pip，也可以使用以下命令安装：

```bash
# 全局安装
pip install pytest-dsl

# 开发模式安装（从本地源码）
pip install -e .
```

## 使用一键安装脚本

项目提供了一键安装脚本，可以自动设置开发环境：

```bash
bash setup_env.sh
```

该脚本会：
1. 安装 uv（如果尚未安装）
2. 创建虚拟环境
3. 安装开发依赖
4. 运行代码迁移脚本

## 验证安装

安装完成后，可以使用以下命令验证安装是否成功：

```bash
# 检查安装的包版本
python -c "import pytest_dsl; print(pytest_dsl.__version__)"

# 运行命令行工具
pytest-dsl --help
```

## 常见问题

### 安装过程中出现权限错误

尝试使用用户安装模式：

```bash
uv pip install --user pytest-dsl
# 或
pip install --user pytest-dsl
```

### 包依赖冲突

uv 通常能够更好地解决依赖冲突。如果使用 pip 时遇到依赖冲突，可以尝试：

```bash
pip install --upgrade pip
pip install pytest-dsl --upgrade
```

### 找不到 pytest-dsl 命令

确保安装目录在您的 PATH 中。对于用户安装，可能需要添加以下目录到 PATH：

- Linux/macOS: `~/.local/bin`
- Windows: `%APPDATA%\Python\Scripts`