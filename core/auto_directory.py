"""自定义目录收集器模块

该模块提供自定义的pytest目录收集器，用于处理.auto文件并将其转换为pytest测试用例。
"""

import sys
import os
import types
import logging
from pathlib import Path
from _pytest import nodes
from typing import Iterable, Union, Optional, List, Dict, Any
import pytest
from filelock import FileLock

from core.dsl_executor import DSLExecutor
from core.dsl_executor_utils import read_file, execute_dsl_file, extract_metadata_from_ast
from core.lexer import get_lexer
from core.parser import get_parser

# 配置日志
logger = logging.getLogger(__name__)

# 获取词法分析器和解析器实例
lexer = get_lexer()
parser = get_parser()

# 用于跟踪已执行的setup和teardown的目录
_setup_executed = set()
_teardown_executed = set()

# 常量定义
SETUP_FILE_NAME = "setup.auto"
TEARDOWN_FILE_NAME = "teardown.auto"
TMP_DIR = "/tmp"
LOCK_FILE_SUFFIX = ".lock"
EXECUTED_FILE_SUFFIX = ".lock.executed"


def get_lock_file_path(dir_path: str, is_setup: bool) -> str:
    """获取锁文件路径
    
    Args:
        dir_path: 目录路径
        is_setup: 是否为setup锁文件
        
    Returns:
        str: 锁文件路径
    """
    prefix = "pytest_dsl_setup_" if is_setup else "pytest_dsl_teardown_"
    return f"{TMP_DIR}/{prefix}{hash(dir_path)}{LOCK_FILE_SUFFIX}"


def execute_hook_file(file_path: Path, is_setup: bool, dir_path_str: str) -> None:
    """执行setup或teardown钩子文件
    
    Args:
        file_path: 钩子文件路径
        is_setup: 是否为setup钩子
        dir_path_str: 目录路径字符串
    """
    hook_type = "Setup" if is_setup else "Teardown"
    executed_set = _setup_executed if is_setup else _teardown_executed
    lock_file = get_lock_file_path(dir_path_str, is_setup)
    
    # 检查是否已执行过
    if dir_path_str in executed_set:
        logger.info(f"{hook_type} for directory already executed: {dir_path_str}")
        return
    
    # 使用filelock获取锁并执行
    with FileLock(lock_file):
        if dir_path_str not in executed_set:  # 再次检查，防止在获取锁期间被其他进程执行
            logger.info(f"Running {hook_type.lower()} for directory: {dir_path_str}")
            if file_path.exists():
                execute_dsl_file(str(file_path))
            # 标记为已执行
            executed_set.add(dir_path_str)
            # 创建标记文件，用于跨进程共享执行状态
            with open(f"{lock_file}{EXECUTED_FILE_SUFFIX}", "w") as f:
                f.write("1")


class AutoDirectory(nodes.Directory):
    """自定义目录收集器，处理.auto文件
    
    该类继承自pytest的Directory收集器，用于收集和处理.auto文件，
    并将它们转换为pytest测试用例。
    """

    def collect(self) -> Iterable[Union[nodes.Item, nodes.Collector]]:
        """收集目录中的.auto文件并创建测试用例
        
        Returns:
            Iterable[Union[nodes.Item, nodes.Collector]]: pytest收集器和测试项
        """
        # 创建模块和设置钩子函数
        module = self._create_module()
        
        # 处理当前目录中的测试文件
        self._process_test_files(module)
        
        # 创建并返回pytest模块
        pytest_module = self._create_pytest_module(module)
        yield pytest_module
        
        # 递归处理子目录
        yield from self._process_subdirectories()
    
    def _create_module(self) -> types.ModuleType:
        """创建模块并设置钩子函数
        
        Returns:
            types.ModuleType: 创建的模块
        """
        module_name = f"auto_module_{self.path.name}"
        
        # 检查setup.auto和teardown.auto文件
        setup_file = self.path / SETUP_FILE_NAME
        teardown_file = self.path / TEARDOWN_FILE_NAME
        
        # 创建或获取模块
        if module_name in sys.modules:
            module = sys.modules[module_name]
        else:
            module = types.ModuleType(module_name)
            sys.modules[module_name] = module
        
        # 创建setup和teardown函数
        setup_function = self._create_setup_function(setup_file)
        teardown_function = self._create_teardown_function(teardown_file)
        
        # 将函数添加到模块
        setattr(module, "setup_module", setup_function)
        setattr(module, "teardown_module", teardown_function)
        
        return module
    
    def _create_setup_function(self, setup_file: Path):
        """创建setup函数
        
        Args:
            setup_file: setup文件路径
            
        Returns:
            function: setup函数
        """
        def setup_function():
            dir_path_str = str(self.path)
            execute_hook_file(setup_file, True, dir_path_str)
        
        return setup_function
    
    def _create_teardown_function(self, teardown_file: Path):
        """创建teardown函数
        
        Args:
            teardown_file: teardown文件路径
            
        Returns:
            function: teardown函数
        """
        def teardown_function():
            dir_path_str = str(self.path)
            execute_hook_file(teardown_file, False, dir_path_str)
        
        return teardown_function
    
    def _process_test_files(self, module: types.ModuleType) -> None:
        """处理目录中的测试文件
        
        Args:
            module: 要添加测试函数的模块
        """
        for auto_file in self.path.glob("*.auto"):
            if auto_file.name not in [SETUP_FILE_NAME, TEARDOWN_FILE_NAME]:
                self._create_test_function(auto_file, module)
    
    def _create_test_function(self, auto_file: Path, module: types.ModuleType) -> None:
        """为.auto文件创建测试函数
        
        Args:
            auto_file: .auto文件路径
            module: 要添加测试函数的模块
        """
        test_name = f"test_{auto_file.stem}"
        
        # 读取DSL文件内容并解析
        dsl_code = read_file(str(auto_file))
        ast = parser.parse(dsl_code, lexer=lexer)
        
        # 检查是否有数据驱动标记和测试名称
        data_source, test_title = extract_metadata_from_ast(ast)
        
        if data_source:
            test_function = self._create_data_driven_test(auto_file, data_source, test_title)
        else:
            test_function = self._create_simple_test(auto_file)
        
        # 将测试函数添加到模块
        setattr(module, test_name, test_function)
    
    def _create_data_driven_test(self, auto_file: Path, data_source: str, test_title: Optional[str]):
        """创建数据驱动的测试函数
        
        Args:
            auto_file: .auto文件路径
            data_source: 数据源
            test_title: 测试标题
            
        Returns:
            function: 装饰后的测试函数
        """
        def test_function(test_data, auto_file=auto_file):
            executor = DSLExecutor()
            executor.set_current_data(test_data)
            execute_dsl_file(str(auto_file), executor)
        
        # 加载测试数据
        executor = DSLExecutor()
        test_data_list = executor._load_test_data(data_source)
        
        # 为每个数据集创建一个唯一的ID
        test_ids = self._generate_test_ids(test_data_list, test_title or auto_file.stem)
        
        # 使用pytest.mark.parametrize装饰测试函数
        return pytest.mark.parametrize(
            'test_data',
            test_data_list,
            ids=test_ids
        )(test_function)
    
    def _generate_test_ids(self, test_data_list: List[Dict[str, Any]], base_name: str) -> List[str]:
        """为数据驱动测试生成ID
        
        Args:
            test_data_list: 测试数据列表
            base_name: 基础名称
            
        Returns:
            List[str]: 测试ID列表
        """
        test_ids = []
        for data in test_data_list:
            # 创建一个可读的测试ID
            test_id = f"{base_name}-{'-'.join(f'{k}={v}' for k, v in data.items())}"
            test_ids.append(test_id)
        return test_ids
    
    def _create_simple_test(self, auto_file: Path):
        """创建普通的测试函数
        
        Args:
            auto_file: .auto文件路径
            
        Returns:
            function: 测试函数
        """
        def test_function(auto_file=auto_file):
            execute_dsl_file(str(auto_file))
        
        return test_function
    
    def _create_pytest_module(self, module: types.ModuleType) -> pytest.Module:
        """创建pytest模块对象
        
        Args:
            module: Python模块
            
        Returns:
            pytest.Module: pytest模块对象
        """
        pytest_module = pytest.Module.from_parent(
            self, path=self.path / f"{module.__name__}.py")
        
        # 重写_getobj方法以返回我们的模块
        def _getobj():
            return module
        
        pytest_module._getobj = _getobj
        
        return pytest_module
    
    def _process_subdirectories(self) -> Iterable[nodes.Collector]:
        """处理子目录
        
        Returns:
            Iterable[nodes.Collector]: 子目录收集器
        """
        for child_path in self.path.glob("*/"):
            if child_path.is_dir():
                child_dir = self.ihook.pytest_collect_directory(
                    path=child_path, parent=self)
                if child_dir is not None:
                    yield child_dir


def init_setup_teardown_tracking() -> None:
    """初始化setup和teardown跟踪状态
    
    从/tmp目录下的标记文件中加载已执行的setup和teardown信息
    """
    global _setup_executed, _teardown_executed
    
    # 扫描/tmp目录下的标记文件
    for filename in os.listdir(TMP_DIR):
        if _is_setup_marker_file(filename):
            dir_hash = _extract_hash_from_filename(filename, True)
            _setup_executed.add(f"hash_{dir_hash}")
        
        if _is_teardown_marker_file(filename):
            dir_hash = _extract_hash_from_filename(filename, False)
            _teardown_executed.add(f"hash_{dir_hash}")


def _is_setup_marker_file(filename: str) -> bool:
    """检查文件名是否为setup标记文件
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 是否为setup标记文件
    """
    return filename.startswith("pytest_dsl_setup_") and filename.endswith(EXECUTED_FILE_SUFFIX)


def _is_teardown_marker_file(filename: str) -> bool:
    """检查文件名是否为teardown标记文件
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 是否为teardown标记文件
    """
    return filename.startswith("pytest_dsl_teardown_") and filename.endswith(EXECUTED_FILE_SUFFIX)


def _extract_hash_from_filename(filename: str, is_setup: bool) -> str:
    """从文件名中提取哈希值
    
    Args:
        filename: 文件名
        is_setup: 是否为setup文件
        
    Returns:
        str: 哈希值
    """
    prefix = "pytest_dsl_setup_" if is_setup else "pytest_dsl_teardown_"
    return filename.replace(prefix, "").replace(EXECUTED_FILE_SUFFIX, "")