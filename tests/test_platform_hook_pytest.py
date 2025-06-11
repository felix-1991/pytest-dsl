"""
pytest格式的测试平台Hook集成测试

运行方式：
python -m pytest tests/test_platform_hook_pytest.py -v -s
"""

import pytest
from tests.test_platform_hook_integration import TestPlatformIntegration


class TestPlatformHookIntegration:
    """使用pytest框架的Hook集成测试"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """pytest fixture用于设置和清理"""
        self.integration = TestPlatformIntegration()
        self.integration.setup_method()
        
        yield
        
        self.integration.teardown_method()
    
    def test_platform_statistics(self):
        """测试平台统计信息"""
        self.integration.test_platform_statistics()
    
    def test_list_cases(self):
        """测试案例列表功能"""
        self.integration.test_list_cases()
    
    def test_environment_variables(self):
        """测试环境变量功能"""
        self.integration.test_environment_variables()
    
    def test_custom_keywords_registration(self):
        """测试自定义关键字注册"""
        self.integration.test_custom_keywords_registration()
    
    def test_execute_dsl_case_by_id(self):
        """测试通过ID执行DSL案例"""
        self.integration.test_execute_dsl_case_by_id()
    
    def test_execute_dsl_case_by_name(self):
        """测试通过名称执行DSL案例"""
        self.integration.test_execute_dsl_case_by_name()
    
    def test_case_management(self):
        """测试案例管理功能"""
        self.integration.test_case_management()
    
    def test_variable_management(self):
        """测试变量管理功能"""
        self.integration.test_variable_management()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 