import pytest
import os


@pytest.fixture(scope="function", autouse=False)
def keep_dsl_variables():
    """
    Pytest fixture to control DSL variable persistence.
    
    Sets PYTEST_DSL_KEEP_VARIABLES=1 to prevent DSLExecutor from clearing variables
    during test execution, which is helpful for testing variable assignments and handling.
    
    Usage:
        1. Apply to specific tests with @pytest.mark.usefixtures("keep_dsl_variables")
        2. Import and use directly: def test_something(keep_dsl_variables):
    """
    # 设置环境变量，使DSL执行器保留变量
    os.environ['PYTEST_DSL_KEEP_VARIABLES'] = '1'
    
    yield
    
    # 测试完成后恢复环境变量
    os.environ.pop('PYTEST_DSL_KEEP_VARIABLES', None) 