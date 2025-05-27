"""自动测试装饰器模块

该模块提供装饰器功能，用于将指定目录下的.auto和.dsl文件动态添加为测试方法到被装饰的类中。
这种方式更贴合pytest的设计理念，可以充分利用pytest的fixture、参数化等功能。
"""

import os
import inspect
import functools
from pathlib import Path
import pytest
from typing import Optional, Union, List, Dict, Any, Callable, Type

from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.dsl_executor_utils import read_file, execute_dsl_file, extract_metadata_from_ast
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import get_parser
from pytest_dsl.core.auto_directory import (
    SETUP_FILE_NAME, TEARDOWN_FILE_NAME,
    SETUP_DSL_FILE_NAME, TEARDOWN_DSL_FILE_NAME,
    execute_hook_file
)

# 获取词法分析器和解析器实例
lexer = get_lexer()
parser = get_parser()


def auto_dsl(directory: Union[str, Path], is_file: bool = False):
    """
    装饰器函数，用于将指定目录下的.auto和.dsl文件动态添加为测试方法到被装饰的类中。

    Args:
        directory: 包含.auto或.dsl文件的目录路径，可以是相对路径或绝对路径
        is_file: 是否是文件路径而不是目录路径

    Returns:
        装饰器函数
    """
    path = Path(directory)
    if not path.is_absolute():
        # 如果是相对路径，则相对于调用者的文件位置
        caller_frame = inspect.currentframe().f_back
        caller_file = caller_frame.f_globals['__file__']
        caller_dir = Path(caller_file).parent
        path = (caller_dir / path).resolve()

    if is_file:
        # 路径是文件
        if not path.exists() or not path.is_file():
            raise ValueError(f"文件不存在或不是有效文件: {path}")
        file_path = path
    else:
        # 路径是目录
        if not path.exists() or not path.is_dir():
            raise ValueError(f"目录不存在或不是有效目录: {path}")
        directory_path = path

    def decorator(cls):
        if is_file:
            # 如果是文件路径，只添加这个文件的测试方法
            _add_test_method(cls, file_path)
        else:
            # 检查setup和teardown文件（支持.auto和.dsl扩展名）
            setup_file = None
            teardown_file = None

            # 优先查找.auto文件，然后查找.dsl文件
            for setup_name in [SETUP_FILE_NAME, SETUP_DSL_FILE_NAME]:
                potential_setup = directory_path / setup_name
                if potential_setup.exists():
                    setup_file = potential_setup
                    break

            for teardown_name in [TEARDOWN_FILE_NAME, TEARDOWN_DSL_FILE_NAME]:
                potential_teardown = directory_path / teardown_name
                if potential_teardown.exists():
                    teardown_file = potential_teardown
                    break

            # 添加setup和teardown方法
            if setup_file:
                @classmethod
                @pytest.fixture(scope="class", autouse=True)
                def setup_class(cls, request):
                    execute_hook_file(setup_file, True, str(directory_path))

                setattr(cls, "setup_class", setup_class)

            if teardown_file:
                @classmethod
                @pytest.fixture(scope="class", autouse=True)
                def teardown_class(cls, request):
                    request.addfinalizer(lambda: execute_hook_file(teardown_file, False, str(directory_path)))

                setattr(cls, "teardown_class", teardown_class)

            # 处理目录中的测试文件，支持.auto和.dsl扩展名
            excluded_files = [SETUP_FILE_NAME, TEARDOWN_FILE_NAME, SETUP_DSL_FILE_NAME, TEARDOWN_DSL_FILE_NAME]
            for pattern in ["*.auto", "*.dsl"]:
                for test_file in directory_path.glob(pattern):
                    if test_file.name not in excluded_files:
                        _add_test_method(cls, test_file)

        return cls

    return decorator


def _add_test_method(cls: Type, test_file: Path) -> None:
    """
    为DSL测试文件创建测试方法并添加到类中

    Args:
        cls: 要添加测试方法的类
        test_file: DSL测试文件路径（.auto或.dsl）
    """
    test_name = f"test_{test_file.stem}"

    # 读取DSL文件内容并解析
    dsl_code = read_file(str(test_file))
    ast = parser.parse(dsl_code, lexer=lexer)

    # 检查是否有数据驱动标记和测试名称
    data_source, test_title = extract_metadata_from_ast(ast)

    if data_source:
        test_method = _create_data_driven_test(test_file, data_source, test_title)
    else:
        test_method = _create_simple_test(test_file)

    # 将测试方法添加到类
    setattr(cls, test_name, test_method)


def _create_simple_test(test_file: Path) -> Callable:
    """
    创建普通的测试方法

    Args:
        test_file: DSL测试文件路径（.auto或.dsl）

    Returns:
        function: 测试方法
    """
    def test_method(self):
        execute_dsl_file(str(test_file))

    return test_method


def _create_data_driven_test(test_file: Path, data_source: Dict, test_title: Optional[str]) -> Callable:
    """
    创建数据驱动的测试方法

    Args:
        test_file: DSL测试文件路径（.auto或.dsl）
        data_source: 数据源
        test_title: 测试标题

    Returns:
        function: 装饰后的测试方法
    """
    def test_method(self, test_data):
        executor = DSLExecutor()
        executor.set_current_data(test_data)
        execute_dsl_file(str(test_file), executor)

    # 加载测试数据
    executor = DSLExecutor()
    test_data_list = executor._load_test_data(data_source)

    # 为每个数据集创建一个唯一的ID
    test_ids = _generate_test_ids(test_data_list, test_title or test_file.stem)

    # 使用pytest.mark.parametrize装饰测试方法
    return pytest.mark.parametrize(
        'test_data',
        test_data_list,
        ids=test_ids
    )(test_method)


def _generate_test_ids(test_data_list: List[Dict[str, Any]], base_name: str) -> List[str]:
    """
    为数据驱动测试生成ID

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