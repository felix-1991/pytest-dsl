import pytest
import types
import sys
from pathlib import Path
from _pytest import nodes
from typing import Iterable, Union, Optional
import os
from filelock import FileLock
from core.global_context import global_context

# 导入DSL相关组件
from core.dsl_executor import DSLExecutor
from core.lexer import get_lexer
from core.parser import get_parser

lexer = get_lexer()
parser = get_parser()

# 用于跟踪已执行的setup和teardown的目录
_setup_executed = set()
_teardown_executed = set()


def read_file(filename):
    """读取 DSL 文件内容"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def execute_dsl_file(file_path):
    """执行DSL文件"""
    if not Path(file_path).exists():
        return
    print(f"执行DSL文件: {file_path}")
    dsl_code = read_file(file_path)
    ast = parser.parse(dsl_code, lexer=lexer)
    executor = DSLExecutor()
    executor.execute(ast)


class AutoDirectory(nodes.Directory):
    """自定义目录收集器，处理.auto文件"""
    
    def collect(self) -> Iterable[Union[nodes.Item, nodes.Collector]]:
        # 为当前目录创建一个模块
        module_name = f"auto_module_{self.path.name}"
        
        # 检查setup.auto和teardown.auto文件
        setup_file = self.path / "setup.auto"
        teardown_file = self.path / "teardown.auto"
        
        # 创建模块
        if module_name in sys.modules:
            module = sys.modules[module_name]
        else:
            module = types.ModuleType(module_name)
            sys.modules[module_name] = module
        
        # 创建setup和teardown函数，使用filelock确保在xdist环境中只执行一次
        def setup_function():
            dir_path_str = str(self.path)
            lock_file = f"/tmp/pytest_dsl_setup_{hash(dir_path_str)}.lock"
            
            # 检查是否已执行过
            if dir_path_str in _setup_executed:
                print(f"Setup for directory already executed: {self.path}")
                return
                
            # 使用filelock获取锁并执行setup
            with FileLock(lock_file):
                if dir_path_str not in _setup_executed:  # 再次检查，防止在获取锁期间被其他进程执行
                    print(f"Running setup for directory: {self.path}")
                    if setup_file.exists():
                        execute_dsl_file(str(setup_file))
                    # 标记为已执行
                    _setup_executed.add(dir_path_str)
                    # 创建标记文件，用于跨进程共享执行状态
                    with open(f"{lock_file}.executed", "w") as f:
                        f.write("1")
        
        def teardown_function():
            dir_path_str = str(self.path)
            lock_file = f"/tmp/pytest_dsl_teardown_{hash(dir_path_str)}.lock"
            
            # 检查是否已执行过
            if dir_path_str in _teardown_executed:
                print(f"Teardown for directory already executed: {self.path}")
                return
                
            # 使用filelock获取锁并执行teardown
            with FileLock(lock_file):
                if dir_path_str not in _teardown_executed:  # 再次检查，防止在获取锁期间被其他进程执行
                    print(f"Running teardown for directory: {self.path}")
                    if teardown_file.exists():
                        execute_dsl_file(str(teardown_file))
                    # 标记为已执行
                    _teardown_executed.add(dir_path_str)
                    # 创建标记文件，用于跨进程共享执行状态
                    with open(f"{lock_file}.executed", "w") as f:
                        f.write("1")
        
        # 将函数添加到模块
        setattr(module, "setup_module", setup_function)
        setattr(module, "teardown_module", teardown_function)
        
        # 收集.auto文件并为每个文件创建测试函数
        for auto_file in self.path.glob("*.auto"):
            if auto_file.name not in ["setup.auto", "teardown.auto"]:
                test_name = f"test_{auto_file.stem}"
                
                # 创建测试函数
                def test_function(auto_file=auto_file):
                    execute_dsl_file(str(auto_file))
                
                # 将测试函数添加到模块
                setattr(module, test_name, test_function)
        
        # 创建pytest Module对象
        pytest_module = pytest.Module.from_parent(self, path=self.path / f"{module_name}.py")
        
        # 重写_getobj方法以返回我们的模块
        def _getobj():
            return module
        
        pytest_module._getobj = _getobj
        
        # 返回模块
        yield pytest_module
        
        # 递归处理子目录
        for child_path in self.path.glob("*/"):
            if child_path.is_dir():
                child_dir = self.ihook.pytest_collect_directory(path=child_path, parent=self)
                if child_dir is not None:
                    yield child_dir


# 在测试会话开始时检查已执行的标记文件
@pytest.hookimpl
def pytest_configure(config):
    """配置测试会话，加载已执行的setup/teardown信息"""
    global _setup_executed, _teardown_executed
    
    # 扫描/tmp目录下的标记文件
    for filename in os.listdir("/tmp"):
        if filename.startswith("pytest_dsl_setup_") and filename.endswith(".lock.executed"):
            dir_hash = filename.replace("pytest_dsl_setup_", "").replace(".lock.executed", "")
            # 这里我们无法直接从哈希值恢复目录路径，但可以在执行时再次检查
            _setup_executed.add(f"hash_{dir_hash}")
        
        if filename.startswith("pytest_dsl_teardown_") and filename.endswith(".lock.executed"):
            dir_hash = filename.replace("pytest_dsl_teardown_", "").replace(".lock.executed", "")
            _teardown_executed.add(f"hash_{dir_hash}")
    
    # 确保全局变量存储目录存在
    os.makedirs(global_context._storage_dir, exist_ok=True)


@pytest.hookimpl
def pytest_collect_directory(path, parent):
    """使用自定义目录收集器处理包含.auto文件的目录"""
    has_auto_files = any(p.suffix == ".auto" for p in path.glob("*.auto"))
    if has_auto_files:
        return AutoDirectory.from_parent(parent=parent, path=path)
    return None